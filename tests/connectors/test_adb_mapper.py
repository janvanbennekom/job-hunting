from datetime import datetime, timezone
from pathlib import Path

from jobhunter.connectors.adb.identity import (
    ADB_CSRN_CMS_APPLICATION_URL,
    ADB_CSRN_LISTING_URL,
    ADB_CSRN_SOURCE_ID,
)
from jobhunter.connectors.adb.mapper import map_adb_notice_to_raw_for_scan
from jobhunter.connectors.adb.parse import parse_listing_page

FIXTURE = Path("tests/fixtures/adb/csrn_listing_sample.html")


def test_map_listing_and_application_urls() -> None:
    notice = parse_listing_page(FIXTURE.read_text(encoding="utf-8"))[3]
    assert notice.notice_id == "E-058125-002"
    record = notice.to_record()
    raw = map_adb_notice_to_raw_for_scan(
        record,
        source_id=ADB_CSRN_SOURCE_ID,
        scan_id="scan-abcd1234-0000",
        retrieved_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    assert raw.source_reference == "E-058125-002"
    assert raw.source_url.startswith(ADB_CSRN_LISTING_URL)
    assert "#notice=E-058125-002" in raw.source_url
    structured = (raw.extra or {}).get("structured_facts") or {}
    assert structured.get("application_url") == ADB_CSRN_CMS_APPLICATION_URL
    assert structured.get("application_url") != raw.source_url
    assert (raw.extra or {}).get("adb_consultant_type") == "Firm"
    assert raw.raw_location == "UZB"
