"""SQLite engine and initialization helpers."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.database.base import Base


def initialize_database() -> Engine:
    """Create the local SQLite file and registered metadata tables."""
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{settings.database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine
