import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Allowed values, kept here so every module uses the same spelling.
STATUSES = ("approved", "rejected", "pending_review")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_public_id() -> str:
    # 16 random bytes -> about 22 URL-safe characters. Not guessable.
    return secrets.token_urlsafe(16)


class Entry(Base):
    __tablename__ = "entries"

    # Internal id: used in the admin, never in a public URL.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Random id: the only id that appears in public URLs.
    public_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=new_public_id
    )

    # What the person submitted
    name: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(255))  # normalised email or phone
    contact_type: Mapped[str] = mapped_column(String(10))  # "email" or "phone"
    story: Mapped[str] = mapped_column(Text)
    consent: Mapped[bool] = mapped_column(Boolean)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Where the entry stands
    status: Mapped[str] = mapped_column(String(20), default="pending_review", index=True)

    # What the AI said (all empty if the AI failed)
    ai_decision: Mapped[str | None] = mapped_column(String(20), default=None)
    ai_reason: Mapped[str | None] = mapped_column(Text, default=None)
    ai_category: Mapped[str | None] = mapped_column(String(20), default=None)
    ai_caption: Mapped[str | None] = mapped_column(String(300), default=None)
    ai_error: Mapped[str | None] = mapped_column(String(200), default=None)  # error TYPE only

    # Bookkeeping
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    admin_override: Mapped[bool] = mapped_column(Boolean, default=False)