"""TED-specific normalizer."""

from __future__ import annotations

from jobhunter.domain.date_placeholders import parse_api_date
from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.opportunity_structured_facts import parse_structured_facts_from_extra
from jobhunter.domain.raw_opportunity import RawOpportunity


class TedOpportunityNormalizer:
    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")
        structured = parse_structured_facts_from_extra(raw.extra or {})
        opportunity_type = OpportunityType.CONSULTANCY
        label = structured.contract_type_label
        if label and "services" not in label.lower() and "consult" not in label.lower():
            opportunity_type = OpportunityType.UNKNOWN
        return NormalizedOpportunity(
            title=title,
            organisation=(raw.raw_organisation or "").strip() or None,
            location=(raw.raw_location or "").strip() or None,
            description=(raw.raw_description or "").strip() or None,
            publication_date=None,
            deadline=parse_api_date(raw.raw_deadline),
            expected_start_date=None,
            opportunity_type=opportunity_type,
            source_status=structured.contract_type_label,
        )
