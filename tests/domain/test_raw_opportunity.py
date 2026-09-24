"""Tests for RawOpportunity."""

from datetime import datetime, timezone

import pytest

from jobhunter.domain import RawOpportunity


def test_raw_opportunity_valid_construction() -> None:
    retrieved = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    raw = RawOpportunity(
        source_id="source-1",
        retrieved_at=retrieved,
        source_reference="WB-123",
        source_url="https://source.example/wb-123",
        raw_title=" GIS Specialist ",
        raw_organisation="Client Org",
        raw_location="Kenya",
        raw_deadline="2026-04-15",
        raw_description="Terms of reference text",
        extra={"notice_type": "procurement", "page": 2},
    )
    assert raw.raw_title == " GIS Specialist "
    assert raw.extra["notice_type"] == "procurement"


def test_raw_opportunity_requires_timezone_aware_retrieved_at() -> None:
    naive = datetime(2026, 3, 1, 12, 0)
    with pytest.raises(ValueError, match="retrieved_at"):
        RawOpportunity(source_id="s1", retrieved_at=naive)


def test_raw_opportunity_preserves_extra_data() -> None:
    retrieved = datetime(2026, 1, 1, tzinfo=timezone.utc)
    raw = RawOpportunity(
        source_id="s1",
        retrieved_at=retrieved,
        extra={"nested": {"a": 1}, "tags": ["gis", "lis"]},
    )
    restored = RawOpportunity.from_mapping(raw.to_mapping())
    assert restored.extra == {"nested": {"a": 1}, "tags": ["gis", "lis"]}


def test_raw_opportunity_mapping_roundtrip() -> None:
    retrieved = datetime(2026, 2, 1, 8, 30, tzinfo=timezone.utc)
    raw = RawOpportunity(
        id="raw-1",
        source_id="s1",
        retrieved_at=retrieved,
        raw_title="Cadastre expert",
    )
    restored = RawOpportunity.from_mapping(raw.to_mapping())
    assert restored == raw
