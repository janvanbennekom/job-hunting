"""Optional live DevelopmentAid API smoke test."""

from __future__ import annotations

import pytest

from jobhunter.connectors.developmentaid.client import DevelopmentAidJobsClient

pytestmark = pytest.mark.live


def test_live_search_and_detail() -> None:
    client = DevelopmentAidJobsClient()
    page = client.search_jobs(page_number=1, page_size=3, keyword="GIS")
    assert page.total > 0
    assert page.items
    job_id = page.items[0]["id"]
    detail = client.get_job(job_id)
    assert detail.get("id") == job_id
    assert detail.get("title")
