"""Tests for FAO -> RawOpportunity mapping."""

from __future__ import annotations

from datetime import datetime, timezone

from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID
from jobhunter.connectors.fao.mapper import map_fao_requisition_to_raw_for_scan


def test_maps_stable_source_reference() -> None:
    record = {
        "jobId": "123",
        "contestNo": "2602999",
        "column": [
            "GIS Specialist",
            "2602999",
            "Non-staff",
            "Consultant",
            "[\"Remote\"]",
            "01/Jan/2026",
            "01/Feb/2026, 11:59:00 PM",
        ],
    }
    retrieved = datetime(2026, 6, 1, tzinfo=timezone.utc)
    raw = map_fao_requisition_to_raw_for_scan(
        record,
        source_id=FAO_JOBS_SOURCE_ID,
        scan_id="scan-a",
        retrieved_at=retrieved,
    )
    assert raw.source_reference == "2602999"
    assert raw.source_id == FAO_JOBS_SOURCE_ID
    assert "123" in raw.source_url
    assert raw.extra["fao_job_id"] == "123"


def test_missing_optional_fields_still_maps() -> None:
    record = {
        "jobId": "555",
        "contestNo": None,
        "column": ["Title only", None, None, None, None, None, None],
    }
    raw = map_fao_requisition_to_raw_for_scan(
        record,
        source_id=FAO_JOBS_SOURCE_ID,
        scan_id="scan-b",
        retrieved_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert raw.source_reference == "555"
    assert raw.raw_location is None


def test_malformed_record_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="jobId"):
        map_fao_requisition_to_raw_for_scan(
            {"contestNo": "x", "column": ["t"]},
            source_id=FAO_JOBS_SOURCE_ID,
            scan_id="scan-c",
            retrieved_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
