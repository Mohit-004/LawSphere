"""SQLite engine and initialization helpers."""

from sqlalchemy import create_engine
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
    return _engine


def get_database_session() -> Iterator[Session]:
    """Yield a short-lived session for one API request."""
    if _engine is None:
        raise RuntimeError("The local database has not been initialized.")
    with Session(_engine) as session:
        yield session
