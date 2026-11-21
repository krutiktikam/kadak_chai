import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.db import Base, get_db
from app.main import app
from app.models import Entry, utcnow


@pytest.fixture
def test_db(tmp_path):
    """Create an isolated SQLite database file for each test."""
    db_file = tmp_path / "test_kadak.db"
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
def client(test_db, monkeypatch):
    """Provide a TestClient with overridden get_db and forced mock AI provider."""
    monkeypatch.setattr(config, "AI_PROVIDER", "mock")

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# Public Route Tests
# ==============================================================================


def test_get_index_renders_form_and_only_approved_stories(client, test_db):
    """GET / should display the submission form and approved entries (first name and caption only)."""
    with test_db() as session:
        # 1. Approved entry
        approved_entry = Entry(
            name="Rohan Verma",
            city="Mumbai",
            contact="rohan.private@example.com",
            contact_type="email",
            story="Every morning, cutting chai by Marine Drive sets the tone for the entire day.",
            consent=True,
            consent_at=utcnow(),
            status="approved",
            ai_caption="Marine Drive cutting chai sets the morning tone.",
            ai_category="nostalgic",
        )

        # 2. Rejected entry
        rejected_entry = Entry(
            name="Spam Bot",
            city="Spamville",
            contact="spambot.private@example.com",
            contact_type="email",
            story="Buy cheap watches at www.spam.example now!",
            consent=True,
            consent_at=utcnow(),
            status="rejected",
            ai_reason="Looks like spam or an advertisement.",
        )

        # 3. Pending review entry
        pending_entry = Entry(
            name="Pending User",
            city="Pune",
            contact="+919876543210",
            contact_type="phone",
            story="Waiting for human moderation on this tea break memory.",
            consent=True,
            consent_at=utcnow(),
            status="pending_review",
            ai_error="provider_timeout",
        )

        session.add_all([approved_entry, rejected_entry, pending_entry])
        session.commit()

    response = client.get("/")
    assert response.status_code == 200

    html = response.text
    # Check dynamic 300-char story limits in template
    assert "10 to 300 characters" in html
    assert 'maxlength="300"' in html
    assert "/ 300" in html

    # Approved first name and caption must be visible
    assert "Rohan" in html
    assert "Marine Drive cutting chai sets the morning tone." in html

    # Privacy enforcement: city and full story must NOT be rendered on public wall
    assert "Mumbai" not in html
    assert "Every morning, cutting chai by Marine Drive" not in html

    # Unapproved content must NOT appear
    assert "Spam Bot" not in html
    assert "Pending User" not in html
    assert "Waiting for human moderation" not in html

    # Private contacts, database IDs, and AI internal errors must NEVER leak
    assert "rohan.private@example.com" not in html
    assert "spambot.private@example.com" not in html
    assert "+919876543210" not in html
    assert "provider_timeout" not in html


def test_post_submit_valid_chai_story_redirects_and_approves(client, test_db):
    """POST /submit with a valid on-topic story redirects 303 to /result/{public_id} and shows approved status."""
    payload = {
        "name": "Aarav Sharma",
        "city": "Jaipur",
        "contact": "aarav.sharma@example.com",
        "story": "Every evening at five, my grandmother brewed strong kadak masala chai with ginger and cardamom for our whole family.",
        "consent": "true",
    }

    response = client.post("/submit", data=payload, follow_redirects=False)
    assert response.status_code == 303

    location = response.headers["location"]
    assert location.startswith("/result/")
    public_id = location.split("/result/")[-1]

    # Verify database persistence
    with test_db() as session:
        entry = session.query(Entry).filter(Entry.public_id == public_id).first()
        assert entry is not None
        assert entry.name == "Aarav Sharma"
        assert entry.city == "Jaipur"
        assert entry.contact == "aarav.sharma@example.com"
        assert entry.contact_type == "email"
        assert entry.status == "approved"
        assert entry.ai_caption is not None
        assert entry.ai_category in ("nostalgic", "wholesome", "funny", "other")
        assert entry.ai_error is None
        caption = entry.ai_caption

    # Follow redirect
    result_response = client.get(location)
    assert result_response.status_code == 200
    result_html = result_response.text
    assert "Approved" in result_html
    assert caption in result_html
    assert "Aarav" in result_html
    # Privacy check: full story, city, and full name are removed
    assert "Jaipur" not in result_html
    assert "Every evening at five, my grandmother brewed" not in result_html


def test_post_submit_spam_story_rejects_and_does_not_show_on_index(client, test_db):
    """POST /submit with spam or off-topic content is rejected and excluded from the public wall."""
    payload = {
        "name": "Spam Advertiser",
        "city": "Unknown",
        "contact": "spammer@example.com",
        "story": "Check out our cheap crypto coins at http://spam.example today for huge profits!",
        "consent": "on",
    }

    response = client.post("/submit", data=payload, follow_redirects=False)
    assert response.status_code == 303

    location = response.headers["location"]
    public_id = location.split("/result/")[-1]

    # Verify DB status is rejected
    with test_db() as session:
        entry = session.query(Entry).filter(Entry.public_id == public_id).first()
        assert entry is not None
        assert entry.status == "rejected"
        assert entry.ai_reason is not None

    # Result page shows generic rejection notice without leaking ai_reason or story
    result_resp = client.get(location)
    assert result_resp.status_code == 200
    assert "Not Selected" in result_resp.text
    assert "did not meet our campaign guidelines" in result_resp.text
    # Privacy check: internal ai_reason, story, and name are not leaked
    assert "crypto" not in result_resp.text
    assert "Spam Advertiser" not in result_resp.text

    # Wall check: must not appear on GET /
    index_resp = client.get("/")
    assert index_resp.status_code == 200
    assert "Spam" not in index_resp.text
    assert "http://spam.example" not in index_resp.text


def test_post_submit_mock_broken_becomes_pending_review_without_leaking_error(client, test_db):
    """POST /submit when AI fails routes to pending_review with generic notice without leaking error."""
    payload = {
        "name": "Divya Rao",
        "city": "Bengaluru",
        "contact": "+91 98765-43210",
        "story": "Chai mock-broken afternoon break with my tech teammates was awesome.",
        "consent": "1",
    }

    response = client.post("/submit", data=payload, follow_redirects=False)
    assert response.status_code == 303

    location = response.headers["location"]
    public_id = location.split("/result/")[-1]

    # Verify DB stores pending_review and ai_error="invalid_json"
    with test_db() as session:
        entry = session.query(Entry).filter(Entry.public_id == public_id).first()
        assert entry is not None
        assert entry.status == "pending_review"
        assert entry.ai_error == "invalid_json"

    # Result page shows reassuring generic message and NEVER leaks "invalid_json", story, or name
    result_resp = client.get(location)
    assert result_resp.status_code == 200
    assert "review" in result_resp.text.lower()
    assert "invalid_json" not in result_resp.text
    assert "Divya" not in result_resp.text
    assert "Chai mock-broken" not in result_resp.text


def test_post_submit_validation_errors_returns_422_and_preserves_input(client):
    """Invalid submissions should return HTTP 422, display field errors, and preserve user input."""
    invalid_payload = {
        "name": "",  # missing
        "city": "Kolkata",
        "contact": "not-a-valid-contact",  # invalid
        "story": "Short",  # too short (< 10)
        "consent": "",  # missing
    }

    response = client.post("/submit", data=invalid_payload)
    assert response.status_code == 422

    html = response.text
    # Field errors should be present
    assert "Name is required." in html
    assert "Enter a valid email address or phone number." in html
    assert "Story must be at least 10 characters." in html
    assert "You must agree to the campaign terms to submit." in html

    # Preserved values
    assert 'value="Kolkata"' in html
    assert 'value="not-a-valid-contact"' in html
    assert "Short" in html


def test_post_submit_story_too_long_returns_422(client):
    """Submitting a story longer than 300 characters returns HTTP 422."""
    payload = {
        "name": "Story Writer",
        "city": "Varanasi",
        "contact": "writer@example.com",
        "story": "Chai " * 65,  # 325 characters (> 300)
        "consent": "true",
    }
    response = client.post("/submit", data=payload)
    assert response.status_code == 422
    assert "Story must be 300 characters or fewer." in response.text


def test_get_result_nonexistent_and_numeric_id_returns_404(client, test_db):
    """GET /result/{public_id} returns 404 for non-existent public IDs and numeric internal IDs."""
    with test_db() as session:
        entry = Entry(
            id=1,
            public_id="real-public-id-abc123xyz",
            name="Sunil Kumar",
            city="Chennai",
            contact="sunil@example.com",
            contact_type="email",
            story="A warm ginger tea by the Marina beach at sunrise.",
            consent=True,
            consent_at=utcnow(),
            status="approved",
            ai_caption="Sunrise chai at Marina Beach",
        )
        session.add(entry)
        session.commit()

    # Numeric ID '1' should not resolve the entry (only public_id is accepted)
    resp_numeric = client.get("/result/1")
    assert resp_numeric.status_code == 404

    # Nonexistent string public_id
    resp_nonexistent = client.get("/result/nonexistent-public-id-99999")
    assert resp_nonexistent.status_code == 404

    # Valid public_id works and shows first name only
    resp_valid = client.get("/result/real-public-id-abc123xyz")
    assert resp_valid.status_code == 200
    assert "Sunil" in resp_valid.text
    assert "Kumar" not in resp_valid.text


def test_xss_protection_escapes_user_input(client):
    """HTML tags in name and story must be escaped to prevent cross-site scripting (XSS)."""
    xss_payload = "<script>alert('xss')</script>"
    payload = {
        "name": xss_payload,
        "city": "Mumbai",
        "contact": "xss.tester@example.com",
        "story": f"Special chai break with {xss_payload} in between meetings.",
        "consent": "yes",
    }

    response = client.post("/submit", data=payload, follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]

    # Check result page: raw script tag must NEVER appear
    result_resp = client.get(location)
    assert result_resp.status_code == 200
    assert "<script>alert('xss')</script>" not in result_resp.text
    assert "&lt;script&gt;" in result_resp.text

    # Check wall page: raw script tag must NEVER appear
    home_resp = client.get("/")
    assert home_resp.status_code == 200
    assert "<script>alert('xss')</script>" not in home_resp.text
    assert "&lt;script&gt;" in home_resp.text


def test_no_mojibake_in_public_pages(client):
    """Submits an approved story in mock mode and asserts '\\u00e2\\u20ac' is not in GET / or GET /result/{public_id}."""
    payload = {
        "name": "Pooja Sharma",
        "city": "Jaipur",
        "contact": "pooja@example.com",
        "story": "Chai with my grandma after school every afternoon.",
        "consent": "yes",
    }
    response = client.post("/submit", data=payload, follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]

    result_resp = client.get(location)
    assert result_resp.status_code == 200
    assert "\u00e2\u20ac" not in result_resp.text

    home_resp = client.get("/")
    assert home_resp.status_code == 200
    assert "\u00e2\u20ac" not in home_resp.text


def test_result_page_open_graph_tags_for_approved_and_pending(client, test_db):
    """Approved result page has og:description with caption; pending result page has no og:description."""
    with test_db() as session:
        approved = Entry(
            name="Kavita Rao",
            city="Bengaluru",
            contact="kavita@example.com",
            contact_type="email",
            story="Filter coffee was regular, but masala chai during monsoon was pure magic.",
            consent=True,
            consent_at=utcnow(),
            status="approved",
            ai_caption="Monsoon masala chai brings pure everyday magic.",
            ai_category="nostalgic",
        )
        pending = Entry(
            name="Devendra Joshi",
            city="Ahmedabad",
            contact="+919876543211",
            contact_type="phone",
            story="Evening chai with snacks after work at the old corner shop.",
            consent=True,
            consent_at=utcnow(),
            status="pending_review",
        )
        session.add_all([approved, pending])
        session.commit()
        approved_id = approved.public_id
        pending_id = pending.public_id

    # Approved entry result page
    resp_app = client.get(f"/result/{approved_id}")
    assert resp_app.status_code == 200
    assert '<meta property="og:description" content="Monsoon masala chai brings pure everyday magic.">' in resp_app.text
    assert '<meta property="og:title"' in resp_app.text
    assert '<meta property="og:url"' in resp_app.text
    assert '<meta property="og:type" content="website">' in resp_app.text
    assert '<meta name="twitter:card" content="summary">' in resp_app.text
    assert "og:image" not in resp_app.text

    # Pending entry result page
    resp_pen = client.get(f"/result/{pending_id}")
    assert resp_pen.status_code == 200
    assert "og:description" not in resp_pen.text
    assert "og:title" not in resp_pen.text

