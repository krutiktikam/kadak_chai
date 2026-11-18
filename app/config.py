import os

from dotenv import load_dotenv

# Read the .env file (if there is one) into environment variables.
# This must happen BEFORE we read any variable below.
load_dotenv()


def _required(name: str) -> str:
    """Return an env var, or stop the app with a clear message."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing environment variable {name}. "
            "Copy .env.example to .env and fill it in."
        )
    return value


# AI settings. "mock" needs no key. Anything else means "call the real provider".
AI_PROVIDER = os.environ.get("AI_PROVIDER", "mock").strip().lower()
AI_BASE_URL = os.environ.get("AI_BASE_URL", "").strip()
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "").strip()

# Admin login and cookie signing. No defaults: a missing secret should crash at startup.
ADMIN_USERNAME = _required("ADMIN_USERNAME")
ADMIN_PASSWORD = _required("ADMIN_PASSWORD")
SECRET_KEY = _required("SECRET_KEY")

# Send the session cookie over HTTPS only. Keep off for local http://127.0.0.1, turn on when deployed.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "").strip().lower() in ("1", "true", "yes")

# Database. SQLite file by default; a hosted Postgres URL when deployed.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./kadak.db")