"""FAO-specific normalizer for Phase 5 processing."""

from __future__ import annotations

from datetime import date, datetime

from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.serialization import deserialize_optional_date

_FAO_DATE_FORMATS = (
    "%d/%b/%Y, %I:%M:%S %p",
    "%d/%b/%Y",
)


def parse_fao_date_text(value: str | None) -> date | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    for fmt in _FAO_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return deserialize_optional_date(text)


class FaoOpportunityNormalizer:
    """Maps FAO RawOpportunity fields into the Phase 5 normalized snapshot."""

    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")

        extra = raw.extra or {}
        publication = extra.get("fao_publication_date")
        opportunity_type = OpportunityType.UNKNOWN
        category = extra.get("fao_opportunity_category")
        if isinstance(category, str):
            lowered = category.lower()
            if "employment" in lowered or "staff" in lowered:
                opportunity_type = OpportunityType.EMPLOYMENT
            elif "consult" in lowered or "non-staff" in lowered:
                opportunity_type = OpportunityType.CONSULTANCY

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
                parse_fao_date_text(str(publication)) if publication else None
            ),
            deadline=parse_fao_date_text(raw.raw_deadline),
            expected_start_date=None,
            opportunity_type=opportunity_type,
            source_status=source_status,
        )
