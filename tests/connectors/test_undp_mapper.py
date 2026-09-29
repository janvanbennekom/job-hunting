from datetime import datetime, timezone
from pathlib import Path

from jobhunter.connectors.rss_feed import parse_rss_items
from jobhunter.connectors.undp.identity import UNDP_JOBS_SOURCE_ID
from jobhunter.connectors.undp.mapper import (
    extract_undp_requisition_id,
    map_undp_item_to_raw_for_scan,
)


def _items() -> list[dict]:
    xml_bytes = Path("tests/fixtures/undp/rss_sample.xml").read_bytes()
    return parse_rss_items(xml_bytes)


def test_requisition_id_from_link() -> None:
    link = "https://estm.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions/job/900101"
    assert extract_undp_requisition_id(link) == "900101"


def test_map_item_deadline_and_reference() -> None:
    item = _items()[0]
    retrieved = datetime(2026, 9, 29, tzinfo=timezone.utc)
    raw = map_undp_item_to_raw_for_scan(
        item,
        source_id=UNDP_JOBS_SOURCE_ID,
        scan_id="scan-abcdef12-0000",
        retrieved_at=retrieved,
    )
    assert raw.source_reference == "900101"
    assert raw.raw_deadline == "15 November 2026"
    assert raw.raw_location == "Nairobi, Kenya"
    assert raw.source_url
