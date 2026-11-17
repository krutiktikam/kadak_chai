from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config


def _fix_url(url: str) -> str:
    """Hosts like Render give 'postgres://' or 'postgresql://'.
    We use the psycopg 3 driver, so SQLAlchemy needs 'postgresql+psycopg://'."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = _fix_url(config.DATABASE_URL)

# SQLite refuses to share a connection between threads unless told otherwise.
# FastAPI runs requests in different threads, so we turn that check off for SQLite only.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: give each request its own session, always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()