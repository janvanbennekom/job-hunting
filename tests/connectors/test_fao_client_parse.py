"""Tests for FAO search response handling."""

from __future__ import annotations

import json
from pathlib import Path

from jobhunter.connectors.fao.client import FaoSearchPage


def test_fixture_search_page_shape() -> None:
    payload = json.loads(
        Path("tests/fixtures/fao/searchjobs_sample.json").read_text(
            encoding="utf-8"
        )
    )
    page = FaoSearchPage(
        requisition_list=list(payload["requisitionList"]),
        current_page=payload["pagingData"]["currentPageNo"],
        page_size=payload["pagingData"]["pageSize"],
        total_count=payload["pagingData"]["totalCount"],
    )
    assert len(page.requisition_list) == 2
    assert page.total_count == 2
