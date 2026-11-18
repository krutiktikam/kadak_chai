import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.security import check_credentials, login_limiter

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
def dashboard(request: Request):
    # Placeholder. Step 3 replaces this with the real entry list.
    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={})
