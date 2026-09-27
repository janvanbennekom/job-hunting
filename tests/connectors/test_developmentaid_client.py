"""Tests for DevelopmentAid client parsing with fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from jobhunter.connectors.developmentaid.client import DevelopmentAidJobsClient

FIXTURE = Path("tests/fixtures/developmentaid/job_search_sample.json")


class _FixtureClient(DevelopmentAidJobsClient):
    def search_jobs(self, **kwargs):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        from jobhunter.connectors.developmentaid.client import DevelopmentAidSearchPage

        return DevelopmentAidSearchPage(
            items=list(payload["items"]),
            total=int(payload["total"]),
            page_number=kwargs.get("page_number", 1),
            page_size=kwargs.get("page_size", 25),
        )


def test_search_returns_items() -> None:
    page = _FixtureClient().search_jobs(page_number=1, page_size=10)
    assert page.total == 2
    assert len(page.items) == 2
