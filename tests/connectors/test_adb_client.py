from pathlib import Path
from unittest.mock import patch

import pytest

from jobhunter.connectors.adb.client import AdbCsrnClient

FIXTURE = Path("tests/fixtures/adb/csrn_listing_sample.html")


def test_client_fetch_from_fixture_html() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    client = AdbCsrnClient()
    with patch.object(client, "_get", return_value=html):
        result = client.fetch_notices(limit=3)
    assert result.pages_fetched == 1
    assert len(result.notices) == 3
    assert result.notices[0]["notice_id"] == "E-059508-001"


def test_client_parser_failure_raises() -> None:
    client = AdbCsrnClient()
    bad = (
        "atResults:imgCsrn:0"
        '<a id="atResults:mstProject:0" title="no id" href="#">x</a></td>'
    )
    with patch.object(client, "_get", return_value=bad):
        with pytest.raises(RuntimeError, match="no notices could be parsed"):
            client.fetch_notices(limit=5)


def test_client_keyword_filter() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    client = AdbCsrnClient()
    with patch.object(client, "_get", return_value=html):
        result = client.fetch_notices(keyword="UZB", limit=25)
    assert all(
        "uzb" in (row.get("title") or "").lower()
        or "uzb" in (row.get("expertise") or "").lower()
        for row in result.notices
    )
