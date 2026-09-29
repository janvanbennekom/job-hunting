"""Tests for World Bank opportunity normalizer."""

from __future__ import annotations

from datetime import datetime, timezone

from jobhunter.connectors.worldbank.identity import WORLDBANK_PROCUREMENT_SOURCE_ID
from jobhunter.connectors.worldbank.normalizer import (
    WorldBankOpportunityNormalizer,
    parse_worldbank_date_text,
)
from jobhunter.domain.raw_opportunity import RawOpportunity


def test_parse_worldbank_dates() -> None:
    assert parse_worldbank_date_text("27-Sep-2026") is not None
    assert parse_worldbank_date_text("2026-09-27T00:00:00Z") is not None


def test_normalize_deadline_from_submission_date() -> None:
    raw = RawOpportunity(
        source_id=WORLDBANK_PROCUREMENT_SOURCE_ID,
        retrieved_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
        raw_title="Consulting services",
        raw_deadline="2026-09-27T00:00:00Z",
        extra={"worldbank_noticedate": "27-Sep-2026"},
    )
    normalized = WorldBankOpportunityNormalizer().normalize(raw)
    assert normalized.deadline is not None
    assert normalized.publication_date is not None
