import re
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.db import Base, get_db
from app.main import app
from app.models import Entry, utcnow
from app.security import login_limiter


@pytest.fixture(autouse=True)
def setup_security_and_limiter(monkeypatch):
    """Ensure clean limiter state and deterministic admin credentials for every test."""
    login_limiter._failures.clear()
    monkeypatch.setattr(config, "ADMIN_USERNAME", "test-admin")
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "test-pass")
    monkeypatch.setattr(config, "AI_PROVIDER", "mock")
    yield
    login_limiter._failures.clear()


@pytest.fixture
def test_db(tmp_path):
    """Create an isolated SQLite database file for each test."""
    db_file = tmp_path / "test_admin.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    session_factory = sessionmaker(bind=test_engine, autoflush=False)
    yield session_factory
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def client(test_db):
    """Provide a TestClient with overridden get_db."""
    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def get_csrf_token(client: TestClient) -> str:
    """Extract CSRF token from the admin dashboard HTML."""
    resp = client.get("/admin")
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.text)
    assert match is not None, "CSRF token not found in dashboard HTML"
    return match.group(1)


# ==============================================================================
# A. Every admin route needs login
# ==============================================================================


def test_every_admin_route_requires_login(client):
    """1. Anonymous requests to protected /admin routes return 303 to /admin/login."""
    checked = 0
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/admin") and path not in ("/admin/login", "/admin/logout"):
            test_path = path.replace("{entry_id}", "1")
            methods = getattr(route, "methods", set()) or {"GET"}
            for method in methods:
                if method == "HEAD":
                    continue
                resp = client.request(method, test_path)
                assert resp.status_code == 303, f"{method} {test_path} gave {resp.status_code}, expected 303"
                assert resp.headers.get("location") == "/admin/login"
                checked += 1

    # 2. Assert the loop found at least 2 routes (dashboard and override)
    assert checked >= 2, f"Expected at least 2 protected admin endpoints, found {checked}"


# ==============================================================================
# B. Login
# ==============================================================================


def test_get_admin_login_returns_200(client):
    """3. GET /admin/login returns 200 with the login form."""
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    assert "Admin login" in resp.text


def test_login_wrong_password_returns_401_no_session(client):
    """4. Wrong password returns 401 and sets no session cookie."""
    resp = client.post("/admin/login", data={"username": "test-admin", "password": "wrong-password"})
    assert resp.status_code == 401
    assert "Invalid username or password." in resp.text
    assert client.cookies.get("session") is None


def test_login_right_credentials_redirects_and_dashboard_accessible(client):
    """5. Right credentials redirect 303 to /admin, and /admin then returns 200."""
    resp = client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    assert resp.status_code == 303
    assert resp.headers.get("location") == "/admin"

    dashboard_resp = client.get("/admin")
    assert dashboard_resp.status_code == 200
    assert "Admin" in dashboard_resp.text


def test_login_five_failures_then_correct_password_blocked_429(client):
    """6. 5 wrong attempts, then correct password returns 429 and /admin remains inaccessible."""
    for _ in range(5):
        r = client.post("/admin/login", data={"username": "test-admin", "password": "bad"})
        assert r.status_code == 401

    # 6th attempt with correct password must be blocked by rate limiter
    r = client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    assert r.status_code == 429
    assert "Too many attempts" in r.text

    # /admin must still be blocked (not authenticated)
    admin_resp = client.get("/admin")
    assert admin_resp.status_code == 303
    assert admin_resp.headers.get("location") == "/admin/login"


def test_logout_redirects_and_clears_session(client):
    """7. Log out redirects 303 to /admin/login, then GET /admin redirects 303."""
    # Login
    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    assert client.get("/admin").status_code == 200

    # Logout
    logout_resp = client.post("/admin/logout")
    assert logout_resp.status_code == 303
    assert logout_resp.headers.get("location") == "/admin/login"

    # Accessing /admin now redirects to login
    r = client.get("/admin")
    assert r.status_code == 303
    assert r.headers.get("location") == "/admin/login"


def test_tampered_or_invalid_secret_session_cookie_redirects_303(client):
    """8. Send a cookie signed with a different secret or tampered value -> 303 to /admin/login."""
    client.cookies.set("session", "tampered-invalid-signature-cookie")
    r = client.get("/admin")
    assert r.status_code == 303
    assert r.headers.get("location") == "/admin/login"


# ==============================================================================
# C. Override
# ==============================================================================


def test_override_missing_and_wrong_csrf_token_returns_403(client, test_db):
    """9. Missing CSRF token / wrong CSRF token returns 403 and status is unchanged in DB."""
    with test_db() as s:
        entry = Entry(
            name="Test User",
            city="Delhi",
            contact="user@example.com",
            contact_type="email",
            story="Chai story text for moderation override.",
            consent=True,
            consent_at=utcnow(),
            status="pending_review",
        )
        s.add(entry)
        s.commit()
        entry_id = entry.id

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})

    # Missing token
    r1 = client.post(f"/admin/entries/{entry_id}/override", data={"decision": "approved"})
    assert r1.status_code == 403

    # Wrong token
    r2 = client.post(f"/admin/entries/{entry_id}/override", data={"decision": "approved", "csrf_token": "wrong-token"})
    assert r2.status_code == 403

    # DB status must remain unchanged
    with test_db() as s:
        check_entry = s.get(Entry, entry_id)
        assert check_entry.status == "pending_review"
        assert check_entry.admin_override is False


def test_override_bad_decision_and_unknown_entry_id(client, test_db):
    """10. Bad decision value returns 400, and unknown entry ID returns 404."""
    with test_db() as s:
        entry = Entry(
            name="Test User",
            city="Delhi",
            contact="user@example.com",
            contact_type="email",
            story="Chai story text for moderation override.",
            consent=True,
            consent_at=utcnow(),
            status="pending_review",
        )
        s.add(entry)
        s.commit()
        entry_id = entry.id

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    token = get_csrf_token(client)

    # Bad decision
    r1 = client.post(f"/admin/entries/{entry_id}/override", data={"decision": "maybe", "csrf_token": token})
    assert r1.status_code == 400

    # Unknown entry ID
    r2 = client.post("/admin/entries/99999/override", data={"decision": "approved", "csrf_token": token})
    assert r2.status_code == 404


def test_override_approve_captionless_pending_entry_without_caption_fails(client, test_db):
    """11. Approve a caption-less pending_review entry with no caption returns 400."""
    with test_db() as s:
        entry = Entry(
            name="Neha Shah",
            city="Surat",
            contact="neha@example.com",
            contact_type="email",
            story="Quiet chai at my desk mock-error",
            consent=True,
            consent_at=utcnow(),
            status="pending_review",
            ai_caption=None,
        )
        s.add(entry)
        s.commit()
        entry_id = entry.id

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    token = get_csrf_token(client)

    r = client.post(f"/admin/entries/{entry_id}/override", data={"decision": "approved", "csrf_token": token, "caption": ""})
    assert r.status_code == 400
    assert "A caption of 1-12 words is needed" in r.text


def test_override_approve_captionless_pending_entry_with_caption_succeeds(client, test_db):
    """12. Approve caption-less pending entry with a valid caption -> 303, updates DB and /result/{public_id}."""
    with test_db() as s:
        entry = Entry(
            name="Neha Shah",
            city="Surat",
            contact="neha@example.com",
            contact_type="email",
            story="Quiet chai at my desk mock-error",
            consent=True,
            consent_at=utcnow(),
            status="pending_review",
            ai_decision=None,
            ai_caption=None,
        )
        s.add(entry)
        s.commit()
        entry_id = entry.id
        public_id = entry.public_id

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    token = get_csrf_token(client)

    r = client.post(
        f"/admin/entries/{entry_id}/override",
        data={"decision": "approved", "csrf_token": token, "caption": "Quiet chai, loud thoughts"},
    )
    assert r.status_code == 303

    with test_db() as s:
        updated = s.get(Entry, entry_id)
        assert updated.status == "approved"
        assert updated.admin_override is True
        assert updated.ai_decision is None
        assert updated.ai_caption == "Quiet chai, loud thoughts"

    # Public page shows the caption
    result_page = client.get(f"/result/{public_id}")
    assert result_page.status_code == 200
    assert "Quiet chai, loud thoughts" in result_page.text


def test_override_reject_approved_entry(client, test_db):
    """13. Reject an approved entry -> 303, /result no longer shows caption, ai_decision is unchanged."""
    with test_db() as s:
        entry = Entry(
            name="Rohan Verma",
            city="Mumbai",
            contact="rohan@example.com",
            contact_type="email",
            story="Morning cutting chai by Marine Drive.",
            consent=True,
            consent_at=utcnow(),
            status="approved",
            ai_decision="approved",
            ai_caption="Marine Drive chai magic",
        )
        s.add(entry)
        s.commit()
        entry_id = entry.id
        public_id = entry.public_id

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    token = get_csrf_token(client)

    r = client.post(
        f"/admin/entries/{entry_id}/override",
        data={"decision": "rejected", "csrf_token": token},
    )
    assert r.status_code == 303

    with test_db() as s:
        updated = s.get(Entry, entry_id)
        assert updated.status == "rejected"
        assert updated.admin_override is True
        assert updated.ai_decision == "approved"  # preserved!

    # Result page no longer shows the caption publicly
    result_page = client.get(f"/result/{public_id}")
    assert result_page.status_code == 200
    assert "Marine Drive chai magic" not in result_page.text


def test_override_open_redirect_prevented(client, test_db):
    """14. back=https://evil.example redirects safely to /admin?status=all."""
    with test_db() as s:
        entry = Entry(
            name="Asha Rao",
            city="Pune",
            contact="asha@example.com",
            contact_type="email",
            story="Evening chai with family.",
            consent=True,
            consent_at=utcnow(),
            status="approved",
            ai_caption="Family chai warmth",
        )
        s.add(entry)
        s.commit()
        entry_id = entry.id

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    token = get_csrf_token(client)

    r = client.post(
        f"/admin/entries/{entry_id}/override",
        data={"decision": "rejected", "csrf_token": token, "back": "https://evil.example"},
    )
    assert r.status_code == 303
    assert r.headers.get("location") == "/admin?status=all"


def test_override_approve_ai_rejected_entry_requires_fresh_caption(client, test_db):
    """Bonus (open decision): Overriding an AI-rejected entry to approved requires a typed caption."""
    with test_db() as s:
        entry = Entry(
            name="Spam Bot",
            city="Goa",
            contact="spambot@example.com",
            contact_type="email",
            story="Buy cheap watches now at http://x.example chai",
            consent=True,
            consent_at=utcnow(),
            status="rejected",
            ai_decision="rejected",
            ai_caption="Not a chai break story",
        )
        s.add(entry)
        s.commit()
        entry_id = entry.id

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    token = get_csrf_token(client)

    # Approving without caption fails
    r1 = client.post(
        f"/admin/entries/{entry_id}/override",
        data={"decision": "approved", "csrf_token": token, "caption": ""},
    )
    assert r1.status_code == 400

    # Approving with caption succeeds and overwrites the rejection caption
    r2 = client.post(
        f"/admin/entries/{entry_id}/override",
        data={"decision": "approved", "csrf_token": token, "caption": "Overridden genuine tea moment"},
    )
    assert r2.status_code == 303

    with test_db() as s:
        updated = s.get(Entry, entry_id)
        assert updated.status == "approved"
        assert updated.ai_caption == "Overridden genuine tea moment"
        assert updated.admin_override is True


# ==============================================================================
# D. Dashboard
# ==============================================================================


def test_dashboard_status_filter(client, test_db):
    """15. Filter pending_review / approved / rejected / bogus lists only matching entries."""
    with test_db() as s:
        s.add_all([
            Entry(name="PendingAsha", city="Pune", contact="a@a.com", contact_type="email", story="Story 1", consent=True, consent_at=utcnow(), status="pending_review"),
            Entry(name="ApprovedRavi", city="Delhi", contact="b@b.com", contact_type="email", story="Story 2", consent=True, consent_at=utcnow(), status="approved", ai_caption="Cap 2"),
            Entry(name="RejectedSpam", city="Goa", contact="c@c.com", contact_type="email", story="Story 3", consent=True, consent_at=utcnow(), status="rejected", ai_reason="Spam"),
        ])
        s.commit()

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})

    # All
    r_all = client.get("/admin", params={"status": "all"})
    assert "PendingAsha" in r_all.text and "ApprovedRavi" in r_all.text and "RejectedSpam" in r_all.text

    # Approved only
    r_app = client.get("/admin", params={"status": "approved"})
    assert "ApprovedRavi" in r_app.text
    assert "PendingAsha" not in r_app.text
    assert "RejectedSpam" not in r_app.text

    # Rejected only
    r_rej = client.get("/admin", params={"status": "rejected"})
    assert "RejectedSpam" in r_rej.text
    assert "ApprovedRavi" not in r_rej.text
    assert "PendingAsha" not in r_rej.text

    # Pending only
    r_pen = client.get("/admin", params={"status": "pending_review"})
    assert "PendingAsha" in r_pen.text
    assert "ApprovedRavi" not in r_pen.text
    assert "RejectedSpam" not in r_pen.text

    # Bogus falls back to all
    r_bogus = client.get("/admin", params={"status": "bogus"})
    assert "PendingAsha" in r_bogus.text and "ApprovedRavi" in r_bogus.text and "RejectedSpam" in r_bogus.text


def test_dashboard_xss_escaping(client, test_db):
    """16. A story containing <script>alert(1)</script> is escaped in dashboard HTML."""
    with test_db() as s:
        entry = Entry(
            name="Tom Lee",
            city="Agra",
            contact="tom@example.com",
            contact_type="email",
            story="<script>alert(1)</script> chai with family",
            consent=True,
            consent_at=utcnow(),
            status="approved",
            ai_caption="Family chai",
        )
        s.add(entry)
        s.commit()

    client.post("/admin/login", data={"username": "test-admin", "password": "test-pass"})
    r = client.get("/admin")
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in r.text
