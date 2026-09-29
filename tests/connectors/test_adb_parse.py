from pathlib import Path

import pytest

from jobhunter.connectors.adb.parse import (
    AdbCsrnParseError,
    extract_country_code,
    extract_notice_id,
    parse_listing_page,
)

FIXTURE = Path("tests/fixtures/adb/csrn_listing_sample.html")


def test_extract_notice_id_from_title() -> None:
    title = "TA-10310 UZB: Example (E-058125-002)"
    assert extract_notice_id(title) == "E-058125-002"


def test_extract_country_code_uzb() -> None:
    title = "TA-10310 UZB: Preparing the Accelerating (E-058125-002)"
    assert extract_country_code(title) == "UZB"


def test_parse_listing_fixture() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    notices = parse_listing_page(html)
    assert len(notices) >= 10
    assert notices[0].notice_id == "E-059508-001"
    assert notices[0].consultant_type == "Firm"
    assert notices[0].published == "24-Sep-2026"
    assert "11:59 PM" in (notices[0].deadline or "")


def test_parse_listing_empty_table() -> None:
    html = "<html>atResults:imgCsrn:0</html>"
    assert parse_listing_page(html) == []


def test_parse_listing_not_csrn_raises() -> None:
    with pytest.raises(AdbCsrnParseError):
        parse_listing_page("<html><body>Not ADB</body></html>")


def test_parse_rows_present_but_unparseable_raises() -> None:
    html = "atResults:mstProject:0 broken row without notice id"
    with pytest.raises(AdbCsrnParseError):
        parse_listing_page(html)
