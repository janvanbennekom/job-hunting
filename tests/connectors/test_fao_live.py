"""Optional live smoke test against FAO (not run in default pytest)."""

from __future__ import annotations

import pytest

from jobhunter.connectors.fao import FaoJobsConnector

pytestmark = pytest.mark.live


def test_live_fao_search_returns_results() -> None:
    connector = FaoJobsConnector()
    result = connector.fetch_requisitions(limit=3)
    assert len(result.records) > 0
