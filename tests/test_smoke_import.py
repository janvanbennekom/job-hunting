"""Phase 0 smoke tests."""

import jobhunter
from jobhunter.infrastructure.config import Settings, get_settings


def test_package_import_and_version() -> None:
    assert jobhunter.__version__ == "0.1.0"


def test_settings_from_environ_defaults() -> None:
    settings = Settings.from_environ({})
    assert settings.env == "development"
    assert settings.log_level == "INFO"
    assert settings.database_url is None


def test_get_settings_uses_process_environ() -> None:
    settings = get_settings({"JOBHUNTER_LOG_LEVEL": "debug"})
    assert settings.log_level == "DEBUG"
