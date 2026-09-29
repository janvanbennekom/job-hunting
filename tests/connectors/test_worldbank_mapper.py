"""Tests for World Bank notice mapping."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jobhunter.connectors.worldbank.identity import WORLDBANK_PROCUREMENT_SOURCE_ID
from jobhunter.connectors.worldbank.mapper import (
    map_worldbank_notice_to_raw,
    map_worldbank_notice_to_raw_for_scan,
    worldbank_notice_detail_url,
)


def _sample_record() -> dict:
    payload = json.loads(
        Path("tests/fixtures/worldbank/procnotices_sample.json").read_text(
            encoding="utf-8"
        )
    )
    return dict(payload["procnotices"][0])


def test_stable_source_reference_and_urls() -> None:
    record = _sample_record()
    notice_id = record["id"]
    retrieved = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    raw = map_worldbank_notice_to_raw(
        record,
        source_id=WORLDBANK_PROCUREMENT_SOURCE_ID,
        retrieved_at=retrieved,
    )
    assert raw.source_reference == notice_id
    assert raw.source_url == worldbank_notice_detail_url(notice_id)
    assert raw.raw_title
    assert raw.raw_description
    assert raw.extra["worldbank_notice_id"] == notice_id
    assert raw.extra["worldbank_project_id"]


def test_scan_mapper_stable_raw_id() -> None:
    record = _sample_record()
    retrieved = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    raw = map_worldbank_notice_to_raw_for_scan(
        record,
        source_id=WORLDBANK_PROCUREMENT_SOURCE_ID,
        scan_id="scan-12345678-abcd",
        retrieved_at=retrieved,
    )
    assert raw.id.startswith("wb-scan1234-")


def test_missing_id_raises() -> None:
    retrieved = datetime(2026, 9, 29, tzinfo=timezone.utc)
    try:
        map_worldbank_notice_to_raw(
            {},
            source_id=WORLDBANK_PROCUREMENT_SOURCE_ID,
            retrieved_at=retrieved,
        )
    except ValueError as exc:
        assert "missing id" in str(exc)
    else:
        raise AssertionError("expected ValueError")
