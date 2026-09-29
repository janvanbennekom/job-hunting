"""Integration tests for DevelopmentAid scan + Phase 5 pipeline."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.developmentaid_scan import DevelopmentAidScanService
from jobhunter.connectors.developmentaid.connector import (
    DevelopmentAidJobsConnector,
    DevelopmentAidScanResult,
)
from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_SOURCE_ID
from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.persistence.models import OpportunityRow
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository
from tests.persistence.isolation_helpers import unique_developmentaid_job_id

pytestmark = pytest.mark.integration

FIXTURE_SEARCH = Path("tests/fixtures/developmentaid/job_search_sample.json")
FIXTURE_DETAIL = Path("tests/fixtures/developmentaid/job_detail_900001.json")


class _FixtureConnector:
    def __init__(self, *, primary_job_id: int | None = None) -> None:
        self._delegate = DevelopmentAidJobsConnector()
        payload = json.loads(FIXTURE_SEARCH.read_text(encoding="utf-8"))
        self._items = [copy.deepcopy(item) for item in payload["items"]]
        self._detail = json.loads(FIXTURE_DETAIL.read_text(encoding="utf-8"))
        job_id = primary_job_id if primary_job_id is not None else unique_developmentaid_job_id()
        self._primary_job_id = job_id
        self._items[0]["id"] = job_id
        detail = copy.deepcopy(self._detail)
        detail["id"] = job_id
        self._details = {str(job_id): detail}

    @property
    def primary_job_id(self) -> int:
        return self._primary_job_id

    def fetch_jobs(self, *, keyword=None, limit=25, fetch_details=True):
        return DevelopmentAidScanResult(
            records=self._items[:limit],
            details=self._details if fetch_details else {},
        )

    def map_to_raw_opportunities(self, *args, **kwargs) -> DevelopmentAidScanResult:
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


def test_job_source_identity(db_session: Session) -> None:
    service = DevelopmentAidScanService(db_session, _FixtureConnector())
    source = service.ensure_job_source()
    assert source.id == DEVELOPMENTAID_JOBS_SOURCE_ID
    assert JobSourceRepository(db_session).get_by_id(DEVELOPMENTAID_JOBS_SOURCE_ID)


def test_scan_success_and_phase5(db_session: Session) -> None:
    connector = _FixtureConnector()
    service = DevelopmentAidScanService(db_session, connector)
    report = service.run_scan(limit=2, apply=True)
    assert report.scan.status is SourceScanStatus.SUCCESS
    assert report.retrieved == 2
    assert report.processed == 2
    assert report.created_opportunities == 2


def test_repeated_scan_no_duplicate(db_session: Session) -> None:
    job_id = unique_developmentaid_job_id()
    connector = _FixtureConnector(primary_job_id=job_id)
    service = DevelopmentAidScanService(db_session, connector)
    first = service.run_scan(limit=1, apply=True)
    second = service.run_scan(limit=1, apply=True)
    assert first.created_opportunities == 1
    assert second.created_opportunities == 0
    count = db_session.scalar(
        select(func.count())
        .select_from(OpportunityRow)
        .where(
            OpportunityRow.canonical_identity_key
            == f"sr:{DEVELOPMENTAID_JOBS_SOURCE_ID}:{job_id}"
        )
    )
    assert count == 1


def test_cross_source_similar_title_no_merge(db_session: Session) -> None:
    from datetime import datetime, timezone

    from jobhunter.application.fao_scan import FaoScanService
    from jobhunter.application.opportunity_processing import OpportunityProcessingService
    from jobhunter.connectors.developmentaid.normalizer import (
        DevelopmentAidOpportunityNormalizer,
    )
    from jobhunter.connectors.fao.normalizer import FaoOpportunityNormalizer

    DevelopmentAidScanService(db_session, _FixtureConnector()).ensure_job_source()
    FaoScanService(db_session).ensure_job_source()

    da_job_id = unique_developmentaid_job_id()
    shared_title = "GIS Specialist for Land Administration"
    da_raw = RawOpportunity(
        id="da-cross-1",
        source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
        source_reference=str(da_job_id),
        source_url=f"https://www.developmentaid.org/jobs/view/{da_job_id}/gis-specialist",
        retrieved_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
        raw_title=shared_title,
        raw_organisation="Org A",
        raw_description="DA description long enough",
        extra={"source_listing_id": str(da_job_id)},
    )
    fao_raw = RawOpportunity(
        id="fao-cross-1",
        source_id=FAO_JOBS_SOURCE_ID,
        source_reference="910000",
        source_url="https://jobs.fao.org/careersection/fao_external/jobdetail.ftl?job=99",
        retrieved_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
        raw_title=shared_title,
        raw_organisation="FAO",
        raw_description="FAO description long enough",
        extra={"fao_job_id": "99"},
    )
    da_proc = OpportunityProcessingService(
        db_session, DevelopmentAidOpportunityNormalizer()
    )
    fao_proc = OpportunityProcessingService(db_session, FaoOpportunityNormalizer())
    da_result = da_proc.process(da_raw)
    fao_result = fao_proc.process(fao_raw)
    assert da_result.created_opportunity is True
    assert fao_result.created_opportunity is True
    assert da_result.opportunity.id != fao_result.opportunity.id
