from jobhunter.connectors.adb.identity import (
    ADB_CSRN_LISTING_URL,
    ADB_CSRN_SOURCE_ID,
)


def test_adb_csrn_source_id() -> None:
    assert ADB_CSRN_SOURCE_ID == "adb-csrn"
    assert "XXCRS_CSRN_HOME_PAGE" in ADB_CSRN_LISTING_URL
