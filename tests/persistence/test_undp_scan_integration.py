from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.undp_scan import UndpScanService
from jobhunter.connectors.rss_feed import parse_rss_items
from jobhunter.connectors.undp.connector import UndpJobsConnector, UndpScanResult
from jobhunter.connectors.undp.identity import UNDP_JOBS_SOURCE_ID
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.persistence.models import OpportunityRow

pytestmark = pytest.mark.integration

FIXTURE = Path("tests/fixtures/undp/rss_sample.xml")


class _FixtureUndpConnector:
    def __init__(self) -> None:
        self._items = parse_rss_items(FIXTURE.read_bytes())
        self._delegate = UndpJobsConnector()

    def fetch_vacancies(self, *, keyword=None, limit=25):
        records = self._items[:limit]
        if keyword:
            needle = keyword.lower()
            records = [
                r for r in records if needle in str(r.get("title") or "").lower()
            ]
        return UndpScanResult(records=records[:limit])

    def map_to_raw_opportunities(self, *args, **kwargs):
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


def test_undp_scan_idempotency(db_session: Session) -> None:
    service = UndpScanService(db_session, _FixtureUndpConnector())
    first = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert first.scan.status is SourceScanStatus.SUCCESS
    assert first.created_opportunities == 2
    second = service.run_scan(limit=2, apply=True, run_profile_assessment=False)
    assert second.created_opportunities == 0
    count = db_session.scalar(
        select(func.count())
        .select_from(OpportunityRow)
        .where(
            OpportunityRow.canonical_identity_key
            == f"sr:{UNDP_JOBS_SOURCE_ID}:900101"
        )
    )
    assert count == 1


def test_malformed_item_partial_scan(db_session: Session) -> None:
    service = UndpScanService(db_session, _FixtureUndpConnector())
    report = service.run_scan(limit=3, apply=True, run_profile_assessment=False)
    assert report.scan.status is SourceScanStatus.PARTIAL
    assert report.processed == 2
    assert report.failed >= 1
