"""Integration tests for TED scan + Phase 5 pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.ted_scan import TedScanService
from jobhunter.connectors.ted.connector import TedProcurementConnector, TedScanResult
from jobhunter.connectors.ted.identity import TED_EU_PROCUREMENT_SOURCE_ID
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.persistence.models import OpportunityRow
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository
from tests.persistence.isolation_helpers import unique_ted_notice_records

pytestmark = pytest.mark.integration

FIXTURE = Path("tests/fixtures/ted/notices_sample.json")


class _FixtureTedConnector:
    def __init__(self, records: list[dict]) -> None:
        self._records = records
        self._delegate = TedProcurementConnector()

    def fetch_notices(self, *, keyword=None, limit=25):
        return TedScanResult(records=self._records[:limit])

    def map_to_raw_opportunities(self, *args, **kwargs):
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


@pytest.fixture
def ted_notices() -> list[dict]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(payload["notices"])


def test_job_source_identity(db_session: Session) -> None:
    service = TedScanService(db_session, _FixtureTedConnector([]))
    source = service.ensure_job_source()
    assert source.id == TED_EU_PROCUREMENT_SOURCE_ID


def test_scan_success_and_idempotency(
    db_session: Session, ted_notices: list[dict]
) -> None:
    isolated = unique_ted_notice_records(ted_notices, count=2)
    service = TedScanService(db_session, _FixtureTedConnector(isolated))
    first = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert first.scan.status is SourceScanStatus.SUCCESS
    assert first.created_opportunities == 2

    second = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert second.created_opportunities == 0

    pub = isolated[0]["publication-number"].lower()
    count = db_session.scalar(
        select(func.count())
        .select_from(OpportunityRow)
        .where(
            OpportunityRow.canonical_identity_key
            == f"sr:{TED_EU_PROCUREMENT_SOURCE_ID}:{pub}"
        )
    )
    assert count == 1
