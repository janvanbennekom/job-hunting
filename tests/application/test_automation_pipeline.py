"""Unit tests for scheduled pipeline orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from jobhunter.ai.fake_model import FakeAssessmentModel
from jobhunter.application.automation.assessment_batch import (
    run_production_assessment_batch,
)
from jobhunter.application.automation.pipeline import ScheduledPipelineOrchestrator
from jobhunter.application.automation.source_adapters import SourceAdapterResult
from jobhunter.domain.automation_enums import AutomationRunStatus
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.automation.config import (
    AutomationConfig,
    NotificationAutomationConfig,
    PipelineAutomationConfig,
    ScheduleConfig,
    SourceAutomationConfig,
)
from jobhunter.infrastructure.config import Settings


class _StubAdapter:
    def __init__(self, key: str, result: SourceAdapterResult) -> None:
        self.key = key
        self._result = result
        self.calls: list[dict] = []

    def run(self, session, source_config, *, apply, run_profile_assessment):
        self.calls.append(
            {
                "apply": apply,
                "run_profile_assessment": run_profile_assessment,
                "key": source_config.key,
            }
        )
        return self._result


def _config(**pipeline_kwargs) -> AutomationConfig:
    return AutomationConfig(
        schedule=ScheduleConfig(enabled=True),
        pipeline=PipelineAutomationConfig(**pipeline_kwargs),
        notifications=NotificationAutomationConfig(enabled=False),
        sources=(
            SourceAutomationConfig(key="fao", enabled=True, limit=2),
            SourceAutomationConfig(key="developmentaid", enabled=True, limit=2),
        ),
    )


def test_dry_run_no_persist_no_assessment_in_scan() -> None:
    fao = _StubAdapter(
        "fao",
        SourceAdapterResult(
            source_key="fao",
            source_id="fao-external-jobs",
            source_scan_id=None,
            scan_status=SourceScanStatus.SUCCESS,
            retrieved=2,
            processed=0,
        ),
    )
    da = _StubAdapter(
        "developmentaid",
        SourceAdapterResult(
            source_key="developmentaid",
            source_id="developmentaid-jobs",
            source_scan_id=None,
            scan_status=SourceScanStatus.SUCCESS,
            retrieved=1,
        ),
    )
    session = MagicMock()
    orchestrator = ScheduledPipelineOrchestrator(
        session,
        _config(production_assessment_enabled=True),
        adapters={"fao": fao, "developmentaid": da},
    )
    result = orchestrator.run(apply=False)
    assert result.dry_run is True
    assert result.automation_run is None
    assert fao.calls[0]["run_profile_assessment"] is False
    assert all(c["apply"] is False for c in fao.calls + da.calls)
    session.merge.assert_not_called()


def test_one_source_failure_other_succeeds_partial() -> None:
    fao = _StubAdapter(
        "fao",
        SourceAdapterResult(
            source_key="fao",
            source_id="fao-external-jobs",
            source_scan_id="scan-1",
            scan_status=SourceScanStatus.SUCCESS,
            retrieved=1,
            processed=1,
            processed_opportunity_ids=["opp-1"],
        ),
    )
    da = _StubAdapter(
        "developmentaid",
        SourceAdapterResult(
            source_key="developmentaid",
            source_id="",
            source_scan_id=None,
            scan_status=None,
            error_message="network down",
        ),
    )
    run_repo = MagicMock()
    saved_run = MagicMock()
    saved_run.id = "run-1"
    run_repo.save.side_effect = lambda entity: entity

    session = MagicMock()
    orchestrator = ScheduledPipelineOrchestrator(
        session,
        _config(),
        adapters={"fao": fao, "developmentaid": da},
    )
    orchestrator._runs = run_repo
    result = orchestrator.run(apply=True)
    assert result.automation_run.status is AutomationRunStatus.PARTIAL
    assert result.exit_code == 1


def test_fake_assessment_rejected_in_production_batch() -> None:
    session = MagicMock()
    with pytest.raises(RuntimeError, match="FakeAssessmentModel"):
        run_production_assessment_batch(
            session,
            ["opp-1"],
            settings=Settings.from_environ({}),
            model_factory=lambda _s: FakeAssessmentModel(),
        )


def test_openai_disabled_skips_assessment() -> None:
    session = MagicMock()
    outcome = run_production_assessment_batch(
        session,
        ["opp-1"],
        settings=Settings.from_environ({}),
    )
    assert outcome.skipped is True
    assert outcome.skip_reason == "openai_not_configured"
