"""Database configuration tests."""

import pytest

from jobhunter.infrastructure.config import get_settings
from jobhunter.infrastructure.persistence.database import create_engine_from_settings


@pytest.mark.integration
def test_database_connectivity() -> None:
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT 1").scalar_one() == 1
    engine.dispose()
