"""DevelopmentAid-specific normalizer for Phase 5 processing."""

from __future__ import annotations

from jobhunter.domain.date_placeholders import parse_api_date
from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.opportunity_structured_facts import parse_structured_facts_from_extra
from jobhunter.domain.raw_opportunity import RawOpportunity


def _opportunity_type_from_contract_label(label: str | None) -> OpportunityType:
    if not label:
        return OpportunityType.UNKNOWN
    lowered = label.lower()
    if "permanent" in lowered or "employment" in lowered:
        return OpportunityType.EMPLOYMENT
    if "contract" in lowered or "consult" in lowered:
        return OpportunityType.CONSULTANCY
    if "intern" in lowered:
        return OpportunityType.OTHER
    return OpportunityType.UNKNOWN


class DevelopmentAidOpportunityNormalizer:
    """Maps DevelopmentAid RawOpportunity fields into the normalized snapshot."""

    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")

        extra = raw.extra or {}
        structured = parse_structured_facts_from_extra(extra)
        contract_label = structured.contract_type_label
        if not contract_label:
            legacy = extra.get("developmentaid_job_type")
            contract_label = legacy.strip() if isinstance(legacy, str) else None

        opportunity_type = _opportunity_type_from_contract_label(contract_label)

        posted_raw = extra.get("source_posted_date") or extra.get(
            "developmentaid_posted_date"
        )
        expected_raw = extra.get("source_expected_start_date") or extra.get(
            "developmentaid_expected_start"
        )

        source_status = extra.get("source_publication_status")
        if source_status is None:
            source_status = extra.get("developmentaid_publication_status")
        if source_status is not None:
            source_status = str(source_status)

        return NormalizedOpportunity(
            title=title,
            organisation=(raw.raw_organisation or "").strip() or None,
            location=(raw.raw_location or "").strip() or None,
            description=(raw.raw_description or "").strip() or None,
            publication_date=parse_api_date(
                str(posted_raw) if posted_raw is not None else None
            ),
            deadline=parse_api_date(raw.raw_deadline),
            expected_start_date=parse_api_date(
                str(expected_raw) if expected_raw is not None else None
            ),
            opportunity_type=opportunity_type,
            source_status=source_status,
        )
