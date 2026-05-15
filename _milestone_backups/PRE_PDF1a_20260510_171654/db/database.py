from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

DATABASE_URL = settings.database_url


def _engine_connect_args(url: str) -> dict[str, Any]:
    """DB-driver connection options; Postgres gets a bounded TCP wait instead of hanging."""
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    lu = url.lower()
    if lu.startswith("postgresql") or lu.startswith("postgres://"):
        # psycopg2 / psycopg (libpq): seconds until connect fails fast
        return {"connect_timeout": 10}
    return {}


engine = create_engine(
    DATABASE_URL,
    connect_args=_engine_connect_args(DATABASE_URL),
    pool_pre_ping=True,
    pool_timeout=30,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
