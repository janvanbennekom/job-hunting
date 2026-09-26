"""Integration tests for FAO scan + Phase 5 pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.fao_scan import FaoScanService
from jobhunter.connectors.fao.connector import FaoJobsConnector, FaoScanResult
from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.persistence.models import OpportunityRow
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository

pytestmark = pytest.mark.integration

FIXTURE = Path("tests/fixtures/fao/searchjobs_sample.json")


class _FixtureFaoConnector:
    def __init__(self, records: list[dict]) -> None:
        self._records = records
        self._delegate = FaoJobsConnector()

    def fetch_requisitions(
        self, *, keyword: str | None = None, limit: int = 25
    ) -> FaoScanResult:
        return FaoScanResult(records=self._records[:limit])

    def map_to_raw_opportunities(self, *args, **kwargs) -> FaoScanResult:
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


@pytest.fixture
def fao_records() -> list[dict]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(payload["requisitionList"])


def test_fao_job_source_identity(db_session: Session) -> None:
    service = FaoScanService(db_session, _FixtureFaoConnector([]))
    source = service.ensure_job_source()
    again = service.ensure_job_source()
    assert source.id == FAO_JOBS_SOURCE_ID
    assert again.id == source.id
    assert JobSourceRepository(db_session).get_by_id(FAO_JOBS_SOURCE_ID) is not None


def test_scan_success_and_phase5_integration(
    db_session: Session, fao_records: list[dict]
) -> None:
    service = FaoScanService(db_session, _FixtureFaoConnector(fao_records))
    report = service.run_scan(limit=2, apply=True)
    assert report.scan.status is SourceScanStatus.SUCCESS
    assert report.retrieved == 2
    assert report.processed == 2
    assert report.created_opportunities == 2


def test_repeated_scan_does_not_duplicate_canonical(
    db_session: Session, fao_records: list[dict]
) -> None:
    connector = _FixtureFaoConnector(fao_records[:1])
    service = FaoScanService(db_session, connector)
    first = service.run_scan(limit=1, apply=True)
    second = service.run_scan(limit=1, apply=True)
    assert first.processed == 1
    assert second.processed == 1
    assert second.created_opportunities == 0
    count = db_session.scalar(
        select(func.count()).select_from(OpportunityRow)
    )
    assert count == 1


def test_scan_partial_failure_on_mapping(
    db_session: Session, fao_records: list[dict]
) -> None:
    broken = list(fao_records) + [{"column": ["No job id"]}]
    service = FaoScanService(db_session, _FixtureFaoConnector(broken))
    report = service.run_scan(limit=3, apply=True)
    assert report.scan.status is SourceScanStatus.PARTIAL
    assert report.failed >= 1
    assert report.processed >= 2


def test_changed_record_triggers_updated(
    db_session: Session, fao_records: list[dict]
) -> None:
    record = dict(fao_records[0])
    columns = list(record["column"])
    service = FaoScanService(db_session, _FixtureFaoConnector([record]))
    service.run_scan(limit=1, apply=True)
    columns[0] = "Land Administration Specialist (revised)"
    record["column"] = columns
    report = service.run_scan(limit=1, apply=True)
    assert report.processed == 1
    assert report.created_opportunities == 0
