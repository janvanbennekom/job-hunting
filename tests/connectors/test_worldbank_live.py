"""Optional live World Bank procnotices smoke test."""

from __future__ import annotations

import pytest

from jobhunter.connectors.worldbank.client import WorldBankProcNoticesClient

pytestmark = pytest.mark.live


def test_live_search_notices() -> None:
    client = WorldBankProcNoticesClient()
    page = client.search_notices(rows=2, offset=0)
    assert page.total > 0
    assert page.notices
    assert page.notices[0].get("id")
