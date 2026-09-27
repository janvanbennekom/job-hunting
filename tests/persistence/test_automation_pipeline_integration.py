"""Integration tests for automation pipeline persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.automation.notification import ConsoleNotificationSender
from jobhunter.application.automation.pipeline import ScheduledPipelineOrchestrator
from jobhunter.application.automation.source_adapters import SourceAdapterResult
from jobhunter.application.developmentaid_scan import DevelopmentAidScanService
from jobhunter.application.fao_scan import FaoScanService
from jobhunter.connectors.developmentaid.connector import (
    DevelopmentAidJobsConnector,
    DevelopmentAidScanResult,
)
from jobhunter.connectors.fao.connector import FaoJobsConnector, FaoScanResult
from jobhunter.domain.automation_enums import AutomationRunStatus
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.automation.config import (
    AutomationConfig,
    NotificationAutomationConfig,
    PipelineAutomationConfig,
    ScheduleConfig,
    SourceAutomationConfig,
)
from jobhunter.infrastructure.persistence.models import AutomationRunRow, SourceScanRow

pytestmark = pytest.mark.integration

FAO_FIXTURE = Path("tests/fixtures/fao/searchjobs_sample.json")
DA_FIXTURE = Path("tests/fixtures/developmentaid/job_search_sample.json")
DA_DETAIL = Path("tests/fixtures/developmentaid/job_detail_900001.json")


class _FixtureFaoConnector:
    def __init__(self) -> None:
        self._delegate = FaoJobsConnector()
        self._records = json.loads(FAO_FIXTURE.read_text(encoding="utf-8"))[
            "requisitionList"
        ]

    def fetch_requisitions(self, *, keyword=None, limit=25) -> FaoScanResult:
        return FaoScanResult(records=self._records[:limit])

    def map_to_raw_opportunities(self, *args, **kwargs) -> FaoScanResult:
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


class _FixtureDaConnector:
    def __init__(self) -> None:
        self._delegate = DevelopmentAidJobsConnector()
        payload = json.loads(DA_FIXTURE.read_text(encoding="utf-8"))
        self._items = payload["items"]
        self._detail = json.loads(DA_DETAIL.read_text(encoding="utf-8"))

    def fetch_jobs(self, *, keyword=None, limit=25, fetch_details=True):
        return DevelopmentAidScanResult(
            records=self._items[:limit],
            details={"900001": self._detail} if fetch_details else {},
        )

    def map_to_raw_opportunities(self, *args, **kwargs) -> DevelopmentAidScanResult:
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


class _FaoAdapter:
    key = "fao"

    def run(self, session, source_config, *, apply, run_profile_assessment):
        service = FaoScanService(session, _FixtureFaoConnector())
        report = service.run_scan(
            limit=source_config.limit,
            apply=apply,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
        )


class _DaAdapter:
    key = "developmentaid"

    def run(self, session, source_config, *, apply, run_profile_assessment):
        service = DevelopmentAidScanService(session, _FixtureDaConnector())
        report = service.run_scan(
            limit=source_config.limit,
            apply=apply,
            fetch_details=source_config.fetch_details,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
        )


def _integration_config() -> AutomationConfig:
    return AutomationConfig(
        schedule=ScheduleConfig(enabled=True),
        pipeline=PipelineAutomationConfig(
            production_assessment_enabled=False,
            ranking_enabled=True,
        ),
        notifications=NotificationAutomationConfig(enabled=True),
        sources=(
            SourceAutomationConfig(key="fao", enabled=True, limit=1),
            SourceAutomationConfig(key="developmentaid", enabled=True, limit=1),
        ),
    )


def test_pipeline_apply_persists_run_and_source_scans(db_session: Session) -> None:
    before_runs = db_session.scalar(select(func.count()).select_from(AutomationRunRow))
    before_scans = db_session.scalar(select(func.count()).select_from(SourceScanRow))
    orchestrator = ScheduledPipelineOrchestrator(
        db_session,
        _integration_config(),
        adapters={"fao": _FaoAdapter(), "developmentaid": _DaAdapter()},
        notification_sender=ConsoleNotificationSender(),
    )
    result = orchestrator.run(apply=True)
    assert result.automation_run is not None
    assert result.automation_run.status in (
        AutomationRunStatus.SUCCESS,
        AutomationRunStatus.PARTIAL,
    )
    after_runs = db_session.scalar(select(func.count()).select_from(AutomationRunRow))
    after_scans = db_session.scalar(select(func.count()).select_from(SourceScanRow))
    assert after_runs == before_runs + 1
    assert after_scans == before_scans + 2


def test_pipeline_dry_run_no_automation_run(db_session: Session) -> None:
    before_runs = db_session.scalar(select(func.count()).select_from(AutomationRunRow))
    orchestrator = ScheduledPipelineOrchestrator(
        db_session,
        _integration_config(),
        adapters={"fao": _FaoAdapter(), "developmentaid": _DaAdapter()},
    )
    result = orchestrator.run(apply=False)
    assert result.automation_run is None
    after_runs = db_session.scalar(select(func.count()).select_from(AutomationRunRow))
    assert after_runs == before_runs
