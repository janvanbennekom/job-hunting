"""Integration tests for ReliefWeb scan + Phase 5 pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.reliefweb_scan import ReliefWebScanService
from jobhunter.connectors.reliefweb.client import ReliefWebJobsClient
from jobhunter.connectors.reliefweb.connector import ReliefWebJobsConnector
from jobhunter.connectors.reliefweb.identity import RELIEFWEB_JOBS_SOURCE_ID
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.persistence.models import OpportunityRow
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository
from tests.persistence.isolation_helpers import unique_reliefweb_job_records

pytestmark = pytest.mark.integration

FIXTURE = Path("tests/fixtures/reliefweb/jobs_sample.json")


class _FixtureReliefWebConnector:
    def __init__(self, records: list[dict]) -> None:
        self._records = records
        self._delegate = ReliefWebJobsConnector(
            ReliefWebJobsClient(appname="fixture-appname")
        )

    def fetch_jobs(self, *, keyword=None, limit=25):
        from jobhunter.connectors.reliefweb.connector import ReliefWebScanResult

        return ReliefWebScanResult(records=self._records[:limit])

    def map_to_raw_opportunities(self, *args, **kwargs):
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


@pytest.fixture
def reliefweb_records() -> list[dict]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(payload["data"])


def test_job_source_identity(db_session: Session) -> None:
    service = ReliefWebScanService(
        db_session, _FixtureReliefWebConnector([])
    )
    source = service.ensure_job_source()
    assert source.id == RELIEFWEB_JOBS_SOURCE_ID
    assert JobSourceRepository(db_session).get_by_id(RELIEFWEB_JOBS_SOURCE_ID)


def test_scan_success_and_idempotency(
    db_session: Session, reliefweb_records: list[dict]
) -> None:
    isolated = unique_reliefweb_job_records(reliefweb_records, count=2)
    service = ReliefWebScanService(
        db_session, _FixtureReliefWebConnector(isolated)
    )
    first = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert first.scan.status is SourceScanStatus.SUCCESS
    assert first.created_opportunities == 2

    second = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert second.created_opportunities == 0

    job_id = str(isolated[0]["id"])
    count = db_session.scalar(
        select(func.count())
        .select_from(OpportunityRow)
        .where(
            OpportunityRow.canonical_identity_key
            == f"sr:{RELIEFWEB_JOBS_SOURCE_ID}:{job_id.lower()}"
        )
    )
    assert count == 1
