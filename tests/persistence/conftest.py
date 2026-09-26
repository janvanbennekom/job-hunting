"""PostgreSQL integration test fixtures (transaction rollback isolation)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from jobhunter.infrastructure.config import get_settings


@pytest.fixture(scope="session")
def database_engine():
    settings = get_settings()
    try:
        url = settings.require_database_url()
    except RuntimeError as exc:
        pytest.skip(str(exc))

    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        has_version_table = conn.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'alembic_version'"
                ")"
            )
        ).scalar()
        if not has_version_table:
            pytest.skip(
                "Alembic migration not applied. Run: alembic upgrade head"
            )
        version = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        if version != "20260926_0003":
            pytest.skip(
                f"Unexpected alembic revision {version!r}; expected 20260926_0003. "
                "Run: alembic upgrade head"
            )
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(database_engine) -> Session:
    """One connection + outer transaction; rolled back after each test."""
    connection = database_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
