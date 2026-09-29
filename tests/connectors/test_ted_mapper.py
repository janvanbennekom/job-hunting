"""Tests for TED notice mapping."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jobhunter.connectors.ted.identity import TED_EU_PROCUREMENT_SOURCE_ID
from jobhunter.connectors.ted.mapper import (
    map_ted_notice_to_raw_for_scan,
    pick_localized_text,
    ted_notice_url,
)

FIXTURE = Path("tests/fixtures/ted/notices_sample.json")


def test_pick_localized_text() -> None:
    assert pick_localized_text({"eng": ["Hello"]}) == "Hello"


def test_maps_publication_number_and_description() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    notice = payload["notices"][0]
    retrieved = datetime(2026, 9, 29, tzinfo=timezone.utc)
    raw = map_ted_notice_to_raw_for_scan(
        notice,
        source_id=TED_EU_PROCUREMENT_SOURCE_ID,
        scan_id="scan-ted",
        retrieved_at=retrieved,
    )
    assert raw.source_reference == "123456-2024"
    assert raw.source_url == ted_notice_url("123456-2024")
    assert "land administration" in (raw.raw_description or "").lower()
