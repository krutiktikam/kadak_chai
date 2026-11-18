import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.schema import MAX_CAPTION_WORDS
from app.db import get_db
from app.models import Entry, utcnow
from app.security import check_credentials, csrf_ok, login_limiter

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def require_admin(request: Request) -> None:
    """Guard: anyone without an admin session is sent to the login page."""
    if request.session.get("admin") is not True:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


def client_ip(request: Request) -> str:
    # Never read X-Forwarded-For ourselves: any client can fake it.
    return request.client.host if request.client else "unknown"


router = APIRouter(prefix="/admin")  # public: login and logout only
protected = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])  # everything else

FILTERS = [
    ("all", "All"),
    ("pending_review", "Pending review"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]
FILTER_KEYS = {key for key, _ in FILTERS}
PAGE_LIMIT = 100
MAX_CAPTION_CHARS = 300  # matches the String(300) column


def _login_error(request: Request, message: str, status: int):
    return templates.TemplateResponse(
        request=request, name="admin_login.html",
        context={"error": message}, status_code=status,
    )


@router.get("/login")
def login_page(request: Request):
    if request.session.get("admin") is True:
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(
        request=request, name="admin_login.html", context={"error": None}
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(default=""),
    password: str = Form(default=""),
):
    ip = client_ip(request)
    if login_limiter.is_blocked(ip):  # checked BEFORE credentials, so a blocked IP learns nothing
        return _login_error(request, "Too many attempts. Please try again later.", 429)
    if not check_credentials(username, password):
        login_limiter.record_failure(ip)
        return _login_error(request, "Invalid username or password.", 401)  # never say which one

    login_limiter.reset(ip)
    request.session.clear()  # start from an empty session, never reuse an old one
    request.session["admin"] = True
    request.session["csrf"] = secrets.token_urlsafe(32)  # used in Step 4
    return RedirectResponse("/admin", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@protected.get("")
def dashboard(request: Request, status: str = "all", db: Session = Depends(get_db)):
    # Only known values are accepted; anything else falls back to "all".
    if status not in FILTER_KEYS:
        status = "all"
    csrf = request.session.setdefault("csrf", secrets.token_urlsafe(32))

    query = db.query(Entry)
    if status != "all":
        query = query.filter(Entry.status == status)
    entries = query.order_by(Entry.created_at.desc(), Entry.id.desc()).limit(PAGE_LIMIT).all()

    rows = db.query(Entry.status, func.count(Entry.id)).group_by(Entry.status).all()
    counts = {key: 0 for key, _ in FILTERS}
    for entry_status, n in rows:
        counts[entry_status] = n
    counts["all"] = sum(n for _, n in rows)

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={"entries": entries, "counts": counts, "filters": FILTERS,
                 "current": status, "limit": PAGE_LIMIT, "csrf": csrf},
    )


@protected.post("/entries/{entry_id}/override")
def override(
    request: Request,
    entry_id: int,
    decision: str = Form(default=""),
    csrf_token: str = Form(default=""),
    caption: str = Form(default=""),
    back: str = Form(default="all"),
    db: Session = Depends(get_db),
):
    if not csrf_ok(request.session.get("csrf"), csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid decision")

    entry = db.get(Entry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    if decision == "approved" and (not entry.ai_caption or entry.ai_decision == "rejected"):
        clean = " ".join(caption.split())
        if not clean or len(clean.split()) > MAX_CAPTION_WORDS or len(clean) > MAX_CAPTION_CHARS:
            raise HTTPException(status_code=400, detail="A caption of 1-12 words is needed to approve")
        entry.ai_caption = clean

    entry.status = decision          # what the site does
    entry.admin_override = True      # ai_decision is never touched: it records what the AI said
    entry.reviewed_at = utcnow()
    db.commit()

    back = back if back in FILTER_KEYS else "all"   # never redirect to a client-supplied URL
    return RedirectResponse(f"/admin?status={back}", status_code=303)
