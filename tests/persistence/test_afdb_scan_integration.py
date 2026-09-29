from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.afdb_scan import AfdbScanService
from jobhunter.connectors.afdb.connector import AfdbConsultantsConnector, AfdbScanResult
from jobhunter.connectors.afdb.detail import parse_afdb_detail_html
from jobhunter.connectors.afdb.identity import AFDB_CONSULTANTS_SOURCE_ID
from jobhunter.connectors.rss_feed import parse_rss_items
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.persistence.models import OpportunityRow

pytestmark = pytest.mark.integration

RSS = Path("tests/fixtures/afdb/consultants_rss_sample.xml")
DETAIL = Path("tests/fixtures/afdb/detail_page_sample.html")


class _FixtureAfdbConnector:
    def __init__(self) -> None:
        self._items = parse_rss_items(RSS.read_bytes())
        self._delegate = AfdbConsultantsConnector()
        self._detail = parse_afdb_detail_html(DETAIL.read_text(encoding="utf-8"))

    def fetch_opportunities(self, *, keyword=None, limit=25, fetch_details=True):
        records = self._items[:limit]
        details = {}
        if fetch_details:
            for item in records:
                from jobhunter.connectors.afdb.mapper import extract_afdb_node_id

                node_id = extract_afdb_node_id(item)
                if node_id:
                    details[node_id] = self._detail
        return AfdbScanResult(records=records, details=details)

    def map_to_raw_opportunities(self, *args, **kwargs):
        return self._delegate.map_to_raw_opportunities(*args, **kwargs)


def test_afdb_scan_idempotency(db_session: Session) -> None:
    service = AfdbScanService(db_session, _FixtureAfdbConnector())
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
            == f"sr:{AFDB_CONSULTANTS_SOURCE_ID}:97090"
        )
    )
    assert count == 1
