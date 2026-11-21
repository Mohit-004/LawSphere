"""SQLite engine and initialization helpers."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from typing import Iterator

from app.core.config import settings
from app.database.base import Base
from app.database import models as _models  # noqa: F401

_engine: Engine | None = None


def initialize_database() -> Engine:
    """Create the local SQLite file and registered metadata tables."""
    global _engine
    if _engine is not None:
        return _engine

    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(
        f"sqlite:///{settings.database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(_engine)
    _apply_sqlite_migrations(_engine)
    return _engine


def _apply_sqlite_migrations(engine: Engine) -> None:
    """Add new nullable/defaulted columns to databases created by earlier slices."""
    with engine.begin() as connection:
        document_columns = {column["name"] for column in inspect(connection).get_columns("documents")}
        if "document_type" not in document_columns:
            connection.execute(text(
                "ALTER TABLE documents ADD COLUMN document_type VARCHAR(10) NOT NULL DEFAULT 'text'"
            ))
        if "stored_path" not in document_columns:
            connection.execute(text("ALTER TABLE documents ADD COLUMN stored_path VARCHAR(4096)"))

        chunk_columns = {column["name"] for column in inspect(connection).get_columns("document_chunks")}
        if "page_number" not in chunk_columns:
            connection.execute(text("ALTER TABLE document_chunks ADD COLUMN page_number INTEGER"))


def get_database_session() -> Iterator[Session]:
    """Yield a short-lived session for one API request."""
    if _engine is None:
        raise RuntimeError("The local database has not been initialized.")
    with Session(_engine) as session:
        yield session
