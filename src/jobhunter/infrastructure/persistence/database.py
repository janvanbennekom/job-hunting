"""SQLAlchemy engine and session setup."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from jobhunter.infrastructure.config import Settings, get_settings


def create_engine_from_settings(settings: Settings | None = None, **engine_kwargs) -> Engine:
    """Create a synchronous SQLAlchemy engine from application settings."""
    resolved = settings or get_settings()
    url = resolved.require_database_url()
    return create_engine(url, **engine_kwargs)


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Commit on success, rollback on error, always close."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
