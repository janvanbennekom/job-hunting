"""Tests for DevelopmentAid -> RawOpportunity mapping."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_SOURCE_ID
from jobhunter.connectors.developmentaid.mapper import (
    map_developmentaid_job_to_raw_for_scan,
)

FIXTURE_DIR = Path("tests/fixtures/developmentaid")


def test_maps_stable_source_reference_and_url() -> None:
    items = json.loads((FIXTURE_DIR / "job_search_sample.json").read_text())[
        "items"
    ]
    detail = json.loads((FIXTURE_DIR / "job_detail_900001.json").read_text())
    retrieved = datetime(2026, 9, 27, tzinfo=timezone.utc)
    raw = map_developmentaid_job_to_raw_for_scan(
        items[0],
        source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
        scan_id="scan-da",
        retrieved_at=retrieved,
        detail=detail,
    )
    assert raw.source_reference == "900001"
    assert "/jobs/view/900001/" in raw.source_url
    assert "land information system" in (raw.raw_description or "").lower()
    assert raw.extra["developmentaid_job_id"] == "900001"


def test_missing_title_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="title"):
        map_developmentaid_job_to_raw_for_scan(
            {"id": 1},
            source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
            scan_id="x",
            retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
