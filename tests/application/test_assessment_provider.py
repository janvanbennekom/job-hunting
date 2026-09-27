"""Operational safety for assessment provider resolution."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.ai.factory import AssessmentProvider, resolve_assessment_model
from jobhunter.ai.fake_model import FakeAssessmentModel
from jobhunter.infrastructure.config import Settings
from jobhunter.infrastructure.persistence.models import OpportunityProfileAssessmentRow


def test_tests_use_fake_model_explicitly() -> None:
    model = FakeAssessmentModel()
    assert model.provider == "fake"
    assert model.model_name == "fake-assessment-v1"


def test_resolve_fake_provider() -> None:
    settings = Settings(
        env="test",
        log_level="INFO",
        database_url=None,
        openai_api_key=None,
        openai_model=None,
    )
    model = resolve_assessment_model(settings, AssessmentProvider.FAKE)
    assert isinstance(model, FakeAssessmentModel)


def test_resolve_openai_without_config_raises() -> None:
    settings = Settings(
        env="test",
        log_level="INFO",
        database_url=None,
        openai_api_key=None,
        openai_model=None,
    )
    with pytest.raises(RuntimeError, match="JOBHUNTER_OPENAI_API_KEY"):
        resolve_assessment_model(settings, "openai")


def test_cli_missing_openai_config_exits_before_db(monkeypatch) -> None:
    import scripts.assess_opportunity_profile as cli

    monkeypatch.setattr(cli, "_load_env", lambda _path: None)
    monkeypatch.delenv("JOBHUNTER_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JOBHUNTER_OPENAI_MODEL", raising=False)

    code = cli.main(
        [
            "--opportunity-id",
            "does-not-matter",
            "--provider",
            "openai",
        ]
    )
    assert code == 1


@pytest.mark.integration
def test_no_assessment_persisted_when_openai_not_configured(
    db_session: Session,
) -> None:
    before = db_session.scalar(
        select(func.count()).select_from(OpportunityProfileAssessmentRow)
    )
    settings = Settings(
        env="test",
        log_level="INFO",
        database_url="postgresql://unused",
        openai_api_key=None,
        openai_model=None,
    )
    with pytest.raises(RuntimeError):
        resolve_assessment_model(settings, "openai")
    after = db_session.scalar(
        select(func.count()).select_from(OpportunityProfileAssessmentRow)
    )
    assert before == after
