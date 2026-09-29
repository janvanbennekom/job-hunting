from datetime import datetime, timezone
from pathlib import Path

from jobhunter.connectors.afdb.detail import parse_afdb_detail_html
from jobhunter.connectors.afdb.identity import AFDB_CONSULTANTS_SOURCE_ID
from jobhunter.connectors.afdb.mapper import (
    extract_afdb_node_id,
    map_afdb_item_to_raw_for_scan,
)
from jobhunter.connectors.rss_feed import parse_rss_items


def _first_item() -> dict:
    xml_bytes = Path("tests/fixtures/afdb/consultants_rss_sample.xml").read_bytes()
    return parse_rss_items(xml_bytes)[0]


def test_node_id_from_guid() -> None:
    item = _first_item()
    assert extract_afdb_node_id(item) == "97090"


def test_map_with_detail_deadline() -> None:
    item = _first_item()
    detail = parse_afdb_detail_html(
        Path("tests/fixtures/afdb/detail_page_sample.html").read_text(encoding="utf-8")
    )
    raw = map_afdb_item_to_raw_for_scan(
        item,
        source_id=AFDB_CONSULTANTS_SOURCE_ID,
        scan_id="scan-abcd1234-0000",
        retrieved_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
        detail=detail,
    )
    assert raw.source_reference == "97090"
    assert raw.raw_deadline == "16-Oct-2026"
    assert "EOI" in raw.raw_title
