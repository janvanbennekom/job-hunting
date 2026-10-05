"""Phase 17H-2 scheduled pipeline hardening behaviour."""

from __future__ import annotations

from unittest.mock import MagicMock

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


class _StubAdapter:
    def __init__(self, key: str, result: SourceAdapterResult) -> None:
        self.key = key
        self._result = result

    def run(self, session, source_config, *, apply, run_profile_assessment):
        return self._result


def _config() -> AutomationConfig:
    return AutomationConfig(
        schedule=ScheduleConfig(enabled=True),
        pipeline=PipelineAutomationConfig(),
        notifications=NotificationAutomationConfig(enabled=False),
        sources=(
            SourceAutomationConfig(key="fao", enabled=True, limit=2),
            SourceAutomationConfig(key="worldbank", enabled=True, limit=2),
        ),
    )


def test_failed_source_does_not_block_next_source() -> None:
    fao = _StubAdapter(
        "fao",
        SourceAdapterResult(
            source_key="fao",
            source_id="",
            source_scan_id=None,
            scan_status=None,
            error_message="network down",
        ),
    )
    wb = _StubAdapter(
        "worldbank",
        SourceAdapterResult(
            source_key="worldbank",
            source_id="worldbank-procurement",
            source_scan_id="scan-2",
            scan_status=SourceScanStatus.SUCCESS,
            retrieved=1,
            processed=1,
            processed_opportunity_ids=["opp-1"],
        ),
    )
    session = MagicMock()
    orchestrator = ScheduledPipelineOrchestrator(
        session,
        _config(),
        adapters={"fao": fao, "worldbank": wb},
    )
    orchestrator._runs = MagicMock()
    orchestrator._runs.save.side_effect = lambda entity: entity

    result = orchestrator.run(apply=True)
    assert result.automation_run.status is AutomationRunStatus.PARTIAL
    assert session.commit.call_count >= 2
    assert len(result.source_results) == 2


def test_run_committed_early_with_running_status() -> None:
    fao = _StubAdapter(
        "fao",
        SourceAdapterResult(
            source_key="fao",
            source_id="fao-external-jobs",
            source_scan_id="scan-1",
            scan_status=SourceScanStatus.SUCCESS,
            retrieved=0,
            processed=0,
        ),
    )
    session = MagicMock()
    wb = _StubAdapter(
        "worldbank",
        SourceAdapterResult(
            source_key="worldbank",
            source_id="worldbank-procurement",
            source_scan_id="scan-2",
            scan_status=SourceScanStatus.SUCCESS,
            retrieved=0,
            processed=0,
        ),
    )
    orchestrator = ScheduledPipelineOrchestrator(
        session,
        _config(),
        adapters={"fao": fao, "worldbank": wb},
    )
    orchestrator._runs = MagicMock()
    orchestrator._runs.save.side_effect = lambda entity: entity

    result = orchestrator.run(apply=True)
    assert result.automation_run.status is AutomationRunStatus.SUCCESS
    first_commit_after_save = session.commit.call_args_list[0]
    assert first_commit_after_save is not None
