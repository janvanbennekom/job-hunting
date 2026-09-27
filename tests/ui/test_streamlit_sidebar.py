"""Streamlit sidebar production behaviour."""

from jobhunter.infrastructure.config import Settings
from jobhunter.ui.streamlit.sidebar import development_assessment_controls_enabled


def test_development_controls_hidden_in_production() -> None:
    settings = Settings(
        env="production",
        log_level="INFO",
        database_url="postgresql://unused",
        openai_api_key=None,
        openai_model=None,
    )
    assert not development_assessment_controls_enabled(settings)


def test_development_controls_visible_in_development() -> None:
    settings = Settings(
        env="development",
        log_level="INFO",
        database_url="postgresql://unused",
        openai_api_key=None,
        openai_model=None,
    )
    assert development_assessment_controls_enabled(settings)
