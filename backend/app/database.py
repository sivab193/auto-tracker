"""Database engine, session factory and declarative base."""
from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _make_engine():
    url = settings.database_url
    connect_args: dict = {}
    if url.startswith("sqlite") and settings.serverless:
        # Serverless filesystems are read-only (and per-instance), so a file
        # SQLite DB would either fail to open or silently lose every write.
        raise RuntimeError(
            "SQLite is not usable in serverless mode — set DATABASE_URL to a "
            "Postgres connection string (e.g. postgresql+psycopg://user:pass@host/db)."
        )
    if url.startswith("sqlite"):
        # Ensure the parent directory for a file-based SQLite DB exists.
        prefix = "sqlite:///"
        if url.startswith(prefix):
            path = url[len(prefix):]
            if path and path not in (":memory:",):
                os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Import models so they register on the metadata."""
    from app import models  # noqa: F401  (side-effect: model registration)

    Base.metadata.create_all(bind=engine)
