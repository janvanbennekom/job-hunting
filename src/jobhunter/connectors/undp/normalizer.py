"""UNDP vacancy normalizer for Phase 5 processing."""

from __future__ import annotations

from datetime import datetime

from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.serialization import deserialize_optional_date

_UNDP_DEADLINE_FORMATS = (
    "%d %B %Y",
    "%d %b %Y",
    "%Y-%m-%d",
)


def parse_undp_deadline_text(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    for fmt in _UNDP_DEADLINE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


class UndpOpportunityNormalizer:
    """Maps UNDP RawOpportunity fields into the Phase 5 normalized snapshot."""

    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")

        opportunity_type = OpportunityType.UNKNOWN
        lowered = title.lower()
        if "consultant" in lowered or "consultancy" in lowered:
            opportunity_type = OpportunityType.CONSULTANCY
        elif "intern" in lowered:
            opportunity_type = OpportunityType.OTHER
        elif "analyst" in lowered or "specialist" in lowered or "officer" in lowered:
            opportunity_type = OpportunityType.EMPLOYMENT

        extra = raw.extra or {}
        publication = extra.get("undp_pub_date")
        pub_date = None
        if publication:
            pub_date = deserialize_optional_date(str(publication)[:10])

        deadline = None
        if raw.raw_deadline:
            dt = parse_undp_deadline_text(raw.raw_deadline)
            if dt is not None:
                deadline = dt.date()
            else:
                deadline = deserialize_optional_date(raw.raw_deadline)

        return NormalizedOpportunity(
            title=title,
            organisation=(raw.raw_organisation or "").strip() or None,
            location=(raw.raw_location or "").strip() or None,
            description=(raw.raw_description or "").strip() or None,
            publication_date=pub_date,
            deadline=deadline,
            expected_start_date=None,
            opportunity_type=opportunity_type,
            source_status=None,
        )
