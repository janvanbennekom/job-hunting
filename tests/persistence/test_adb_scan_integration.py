from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.adb_scan import AdbScanService
from jobhunter.connectors.adb.connector import AdbCsrnConnector, AdbCsrnScanResult
from jobhunter.connectors.adb.identity import ADB_CSRN_SOURCE_ID
from jobhunter.connectors.adb.parse import parse_listing_page
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.application.profile_assessment.source_sufficiency import (
    infer_source_data_sufficiency,
)
from jobhunter.infrastructure.persistence.models import OpportunityRow
from tests.persistence.isolation_helpers import unique_adb_notice_records

pytestmark = pytest.mark.integration

FIXTURE = Path("tests/fixtures/adb/csrn_listing_sample.html")


class _FixtureAdbConnector:
    def __init__(self) -> None:
        notices = parse_listing_page(FIXTURE.read_text(encoding="utf-8"))
        by_id: dict[str, object] = {}
        for notice in notices:
            if notice.notice_id not in by_id:
                by_id[notice.notice_id] = notice
        base = [n.to_record() for n in by_id.values()][:5]
        self._records = unique_adb_notice_records(base, count=min(5, len(base)))
        self._delegate = AdbCsrnConnector()

    def fetch_notices(self, *, keyword=None, limit=25, fetch_details=False):
        rows = self._records[:limit]
        if keyword and keyword.strip():
            needle = keyword.strip().lower()
            rows = [
                r
                for r in rows
                if needle in (r.get("title") or "").lower()
                or needle in (r.get("expertise") or "").lower()
            ]
        return AdbCsrnScanResult(records=rows[:limit], pages_fetched=1)

    def map_to_raw_opportunities(self, *args, **kwargs):
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


def test_adb_scan_idempotency(db_session: Session) -> None:
    service = AdbScanService(db_session, _FixtureAdbConnector())
    first = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert first.scan.status is SourceScanStatus.SUCCESS
    assert first.created_opportunities == 2
    second = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert second.created_opportunities == 0
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

    opp = OpportunityRepository(db_session).get_by_id(
        first.processed_opportunity_ids[0]
    )
    assert opp is not None
    assert opp.canonical_identity_key is not None
    count = db_session.scalar(
        select(func.count())
        .select_from(OpportunityRow)
        .where(OpportunityRow.canonical_identity_key == opp.canonical_identity_key)
    )
    assert count == 1


def test_adb_source_data_sufficiency_partial() -> None:
    connector = _FixtureAdbConnector()
    fetch = connector.fetch_notices(limit=1)
    mapping = connector.map_to_raw_opportunities(
        fetch,
        source_id=ADB_CSRN_SOURCE_ID,
        scan_id="scan-test-0001",
    )
    raw = mapping.raw_opportunities[0]
    opp = Opportunity(
        title=raw.raw_title or "",
        description=raw.raw_description,
    )
    suff = infer_source_data_sufficiency(opp, primary_source_id=ADB_CSRN_SOURCE_ID)
    assert suff.value == "PARTIAL"
