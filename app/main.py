from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import config
from app.ai import analyze_story
from app.db import Base, engine, get_db
from app.models import Entry, utcnow
from app.validation import SubmissionValidationError, validate_submission

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: create any missing tables.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))  # fails if the database is unreachable
    return {"status": "ok", "ai_provider": config.AI_PROVIDER}


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    """Display campaign submission form and approved story wall."""
    approved_entries = (
        db.query(Entry)
        .filter(Entry.status == "approved")
        .order_by(Entry.created_at.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"entries": approved_entries, "errors": {}, "form_data": {}},
    )


@app.post("/submit")
def submit_story(
    request: Request,
    name: str = Form(default=""),
    city: str = Form(default=""),
    contact: str = Form(default=""),
    story: str = Form(default=""),
    consent: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Validate submission, run AI moderation, persist entry, and redirect to result page."""
    try:
        valid = validate_submission(name, city, contact, story, consent)
    except SubmissionValidationError as exc:
        approved_entries = (
            db.query(Entry)
            .filter(Entry.status == "approved")
            .order_by(Entry.created_at.desc())
            .limit(20)
            .all()
        )
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "entries": approved_entries,
                "errors": exc.errors,
                "form_data": {
                    "name": name,
                    "city": city,
                    "contact": contact,
                    "story": story,
                    "consent": consent,
                },
            },
            status_code=422,
        )

    # Moderate via AI (mock or real configured provider)
    outcome = analyze_story(valid.story)

    entry = Entry(
        name=valid.name,
        city=valid.city,
        contact=valid.contact,
        contact_type=valid.contact_type,
        story=valid.story,
        consent=valid.consent,
        consent_at=utcnow(),
        status=outcome.status,
        ai_decision=outcome.ai_decision,
        ai_reason=outcome.ai_reason,
        ai_category=outcome.ai_category,
        ai_caption=outcome.ai_caption,
        ai_error=outcome.ai_error,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Post/Redirect/Get pattern prevents duplicate submissions on refresh
    return RedirectResponse(url=f"/result/{entry.public_id}", status_code=303)


@app.get("/result/{public_id}")
def view_result(request: Request, public_id: str, db: Session = Depends(get_db)):
    """Display submission outcome for the given public_id."""
    entry = db.query(Entry).filter(Entry.public_id == public_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={"entry": entry},
    )
