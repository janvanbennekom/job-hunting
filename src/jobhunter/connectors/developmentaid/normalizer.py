"""DevelopmentAid-specific normalizer for Phase 5 processing."""

from __future__ import annotations

from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.serialization import deserialize_optional_date


class DevelopmentAidOpportunityNormalizer:
    """Maps DevelopmentAid RawOpportunity fields into the normalized snapshot."""

    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")

        extra = raw.extra or {}
        job_type = extra.get("developmentaid_job_type")
        opportunity_type = OpportunityType.UNKNOWN
        if isinstance(job_type, str):
            lowered = job_type.lower()
            if "permanent" in lowered or "employment" in lowered:
                opportunity_type = OpportunityType.EMPLOYMENT
            elif "contract" in lowered or "consult" in lowered:
                opportunity_type = OpportunityType.CONSULTANCY
            elif "intern" in lowered:
                opportunity_type = OpportunityType.OTHER

        publication = extra.get("developmentaid_posted_date")
        expected_start = extra.get("developmentaid_expected_start")

        return NormalizedOpportunity(
            title=title,
            organisation=(raw.raw_organisation or "").strip() or None,
            location=(raw.raw_location or "").strip() or None,
            description=(raw.raw_description or "").strip() or None,
            publication_date=(
                deserialize_optional_date(str(publication))
                if publication
                else None
            ),
            deadline=deserialize_optional_date(raw.raw_deadline),
            expected_start_date=(
                deserialize_optional_date(str(expected_start))
                if expected_start
                else None
            ),
            opportunity_type=opportunity_type,
            source_status=extra.get("developmentaid_publication_status"),
        )
