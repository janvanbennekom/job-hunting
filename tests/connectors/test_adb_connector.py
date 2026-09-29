from datetime import datetime, timezone

from jobhunter.connectors.adb.connector import AdbCsrnConnector
from jobhunter.connectors.adb.identity import ADB_CSRN_SOURCE_ID


def test_fetch_details_adds_warning() -> None:
    class _StubClient:
        def fetch_notices(self, **kwargs):
            from jobhunter.connectors.adb.client import AdbCsrnListingResult

            return AdbCsrnListingResult(notices=[], pages_fetched=0)

    connector = AdbCsrnConnector(_StubClient())
    result = connector.fetch_notices(limit=1, fetch_details=True)
    assert any("fetch_details is ignored" in err for err in result.errors)


def test_malformed_row_does_not_fail_whole_map() -> None:
    connector = AdbCsrnConnector()
    from jobhunter.connectors.adb.connector import AdbCsrnScanResult

    fetch = AdbCsrnScanResult(
        records=[
            {"notice_id": "E-000001-001", "title": "Valid (E-000001-001)"},
            {"notice_id": "", "title": ""},
        ]
    )
    mapped = connector.map_to_raw_opportunities(
        fetch,
        source_id=ADB_CSRN_SOURCE_ID,
        scan_id="scan-abcd1234-0000",
        retrieved_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    assert len(mapped.raw_opportunities) == 1
    assert len(mapped.errors) == 1
