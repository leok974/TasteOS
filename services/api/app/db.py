from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .settings import settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def init_engine(database_url: str | None = None):
    global _engine, _SessionLocal
    url = database_url or settings.database_url
    _engine = create_engine(url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_engine():
    global _engine
    if _engine is None:
        init_engine()
    return _engine


def SessionLocal():
    global _SessionLocal
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal


def get_db():
    db = SessionLocal()()
    try:
        yield db
    finally:
        db.close()
