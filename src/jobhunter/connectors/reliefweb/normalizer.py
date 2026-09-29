"""ReliefWeb-specific normalizer."""

from __future__ import annotations

from jobhunter.domain.date_placeholders import parse_api_date
from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.opportunity_structured_facts import parse_structured_facts_from_extra
from jobhunter.domain.raw_opportunity import RawOpportunity


def _opportunity_type_from_label(label: str | None) -> OpportunityType:
    if not label:
        return OpportunityType.UNKNOWN
    lowered = label.lower()
    if "consult" in lowered or "contract" in lowered:
        return OpportunityType.CONSULTANCY
    if "staff" in lowered or "employment" in lowered:
        return OpportunityType.EMPLOYMENT
    return OpportunityType.UNKNOWN


class ReliefWebOpportunityNormalizer:
    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")
        extra = raw.extra or {}
        structured = parse_structured_facts_from_extra(extra)
        return NormalizedOpportunity(
            title=title,
            organisation=(raw.raw_organisation or "").strip() or None,
            location=(raw.raw_location or "").strip() or None,
            description=(raw.raw_description or "").strip() or None,
            publication_date=parse_api_date(
                str(extra.get("source_posted_date"))
                if extra.get("source_posted_date")
                else None
            ),
            deadline=parse_api_date(raw.raw_deadline),
            expected_start_date=None,
            opportunity_type=_opportunity_type_from_label(
                structured.contract_type_label
            ),
            source_status=None,
        )
