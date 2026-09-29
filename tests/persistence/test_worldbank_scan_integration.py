"""Integration tests for World Bank scan + Phase 5 pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.fao_scan import FaoScanService
from jobhunter.application.opportunity_processing import OpportunityProcessingService
from jobhunter.application.worldbank_scan import WorldBankScanService
from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID
from jobhunter.connectors.fao.normalizer import FaoOpportunityNormalizer
from jobhunter.connectors.worldbank.connector import (
    WorldBankProcNoticesConnector,
    WorldBankScanResult,
)
from jobhunter.connectors.worldbank.identity import WORLDBANK_PROCUREMENT_SOURCE_ID
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.persistence.models import OpportunityRow
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository

pytestmark = pytest.mark.integration

FIXTURE = Path("tests/fixtures/worldbank/procnotices_sample.json")


class _FixtureWorldBankConnector:
    def __init__(self, records: list[dict]) -> None:
        self._records = records
        self._delegate = WorldBankProcNoticesConnector()

    def fetch_notices(self, *, keyword: str | None = None, limit: int = 25):
        return WorldBankScanResult(records=self._records[:limit])

    def map_to_raw_opportunities(self, *args, **kwargs) -> WorldBankScanResult:
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


@pytest.fixture
def worldbank_records() -> list[dict]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(payload["procnotices"])


def test_worldbank_job_source_identity(db_session: Session) -> None:
    service = WorldBankScanService(db_session, _FixtureWorldBankConnector([]))
    source = service.ensure_job_source()
    assert source.id == WORLDBANK_PROCUREMENT_SOURCE_ID
    assert JobSourceRepository(db_session).get_by_id(WORLDBANK_PROCUREMENT_SOURCE_ID)


def test_scan_success_and_idempotency(
    db_session: Session, worldbank_records: list[dict]
) -> None:
    service = WorldBankScanService(
        db_session, _FixtureWorldBankConnector(worldbank_records)
    )
    first = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert first.scan.status is SourceScanStatus.SUCCESS
    assert first.retrieved == 2
    assert first.created_opportunities == 2

    second = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert second.created_opportunities == 0

    notice_id = worldbank_records[0]["id"].lower()
    count = db_session.scalar(
        select(func.count())
        .select_from(OpportunityRow)
        .where(
            OpportunityRow.canonical_identity_key
            == f"sr:{WORLDBANK_PROCUREMENT_SOURCE_ID}:{notice_id}"
        )
    )
    assert count == 1


def test_cross_source_same_reference_no_merge(
    db_session: Session, worldbank_records: list[dict]
) -> None:
    from datetime import datetime, timezone

    from jobhunter.connectors.worldbank.normalizer import WorldBankOpportunityNormalizer

    WorldBankScanService(db_session, _FixtureWorldBankConnector([])).ensure_job_source()
    FaoScanService(db_session).ensure_job_source()

    shared_ref = worldbank_records[0]["id"]
    shared_title = "GIS and Land Administration Consultant"
    wb_raw = RawOpportunity(
        id="wb-cross-1",
        source_id=WORLDBANK_PROCUREMENT_SOURCE_ID,
        source_reference=shared_ref,
        source_url="https://projects.worldbank.org/en/projects-operations/procurement-detail/x",
        retrieved_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
        raw_title=shared_title,
        raw_description="World Bank notice description with sufficient detail.",
        extra={"worldbank_notice_id": shared_ref},
    )
    fao_raw = RawOpportunity(
        id="fao-cross-1",
        source_id=FAO_JOBS_SOURCE_ID,
        source_reference=shared_ref,
        source_url="https://jobs.fao.org/careersection/fao_external/jobdetail.ftl?job=1",
        retrieved_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
        raw_title=shared_title,
        raw_description="FAO description with sufficient detail.",
        extra={"fao_job_id": "1"},
    )
    wb_proc = OpportunityProcessingService(db_session, WorldBankOpportunityNormalizer())
    fao_proc = OpportunityProcessingService(db_session, FaoOpportunityNormalizer())
    wb_result = wb_proc.process(wb_raw)
    fao_result = fao_proc.process(fao_raw)
    assert wb_result.opportunity.id != fao_result.opportunity.id
