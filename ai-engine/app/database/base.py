"""Shared SQLAlchemy declarative base for future metadata models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
