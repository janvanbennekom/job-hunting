"""AfDB consultant opportunity normalizer."""

from __future__ import annotations

from datetime import datetime

from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.serialization import deserialize_optional_date

_AFDB_DATE_FORMATS = ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d")


def parse_afdb_date_text(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    for fmt in _AFDB_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


class AfdbOpportunityNormalizer:
    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")

        opportunity_type = OpportunityType.UNKNOWN
        if title.upper().startswith("EOI") or "consultant" in title.lower():
            opportunity_type = OpportunityType.CONSULTANCY

        extra = raw.extra or {}
        publication = extra.get("afdb_pub_date")
        pub_date = deserialize_optional_date(str(publication)[:10]) if publication else None

        deadline = None
        if raw.raw_deadline:
            dt = parse_afdb_date_text(raw.raw_deadline)
            deadline = dt.date() if dt else deserialize_optional_date(raw.raw_deadline)

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
