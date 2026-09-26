"""Fixture-oriented normalizer for Phase 5 pipeline tests and development."""

from __future__ import annotations

from datetime import date

from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.serialization import deserialize_optional_date


def _parse_deadline(raw_deadline: str | None) -> date | None:
    if raw_deadline is None or not str(raw_deadline).strip():
        return None
    text = str(raw_deadline).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return deserialize_optional_date(text)


def _parse_opportunity_type(extra: dict) -> OpportunityType:
    value = extra.get("opportunity_type")
    if not isinstance(value, str) or not value.strip():
        return OpportunityType.UNKNOWN
    try:
        return OpportunityType(value.strip().upper())
    except ValueError:
        return OpportunityType.UNKNOWN


class FixtureOpportunityNormalizer:
    """Deterministic normalizer for representative raw fixture payloads."""

    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")

        extra = raw.extra or {}
        publication = extra.get("publication_date")
        expected_start = extra.get("expected_start_date")
        source_status = extra.get("source_status")
        if isinstance(source_status, str):
            source_status = source_status.strip() or None
        else:
            source_status = None

        return NormalizedOpportunity(
            title=title,
            organisation=(raw.raw_organisation or "").strip() or None,
            location=(raw.raw_location or "").strip() or None,
            description=(raw.raw_description or "").strip() or None,
            publication_date=(
                deserialize_optional_date(publication)
                if publication
                else None
            ),
            deadline=_parse_deadline(raw.raw_deadline),
            expected_start_date=(
                deserialize_optional_date(expected_start)
                if expected_start
                else None
            ),
            opportunity_type=_parse_opportunity_type(extra),
            source_status=source_status,
        )
