from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import config
from app import models  # noqa: F401  (importing this registers the Entry table)
from app.db import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: create any missing tables.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))  # fails if the database is unreachable
    return {"status": "ok", "ai_provider": config.AI_PROVIDER}