"""Tests for FAO date normalization."""

from __future__ import annotations

from datetime import date, datetime, timezone

from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID
from jobhunter.connectors.fao.normalizer import FaoOpportunityNormalizer, parse_fao_date_text
from jobhunter.domain.raw_opportunity import RawOpportunity


def test_parse_fao_deadline() -> None:
    assert parse_fao_date_text("31/Dec/2026, 11:59:00 PM") == date(2026, 12, 31)


def test_normalizer_applies_fao_deadline() -> None:
    raw = RawOpportunity(
        source_id=FAO_JOBS_SOURCE_ID,
        retrieved_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        raw_title="Example",
        raw_deadline="15/Mar/2026, 11:59:00 PM",
        extra={"fao_publication_date": "01/Jan/2026"},
    )
    normalized = FaoOpportunityNormalizer().normalize(raw)
    assert normalized.deadline == date(2026, 3, 15)
    assert normalized.publication_date == date(2026, 1, 1)
