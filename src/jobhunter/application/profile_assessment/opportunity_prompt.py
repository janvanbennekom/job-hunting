"""Build opportunity text supplied to the assessment model."""

from __future__ import annotations

from jobhunter.domain.assessment_enums import OpportunityEvidenceField
from jobhunter.domain.opportunity import Opportunity

_MAX_FIELD_LENGTH = 12_000


def _truncate(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if len(text) <= _MAX_FIELD_LENGTH:
        return text
    return text[:_MAX_FIELD_LENGTH]


def build_opportunity_prompt_text(
    opportunity: Opportunity,
) -> dict[str, str]:
    return {
        OpportunityEvidenceField.TITLE.value: _truncate(opportunity.title),
        OpportunityEvidenceField.DESCRIPTION.value: _truncate(
            opportunity.description
        ),
        OpportunityEvidenceField.LOCATION.value: _truncate(opportunity.location),
        OpportunityEvidenceField.ORGANISATION.value: _truncate(
            opportunity.organisation
        ),
        OpportunityEvidenceField.OPPORTUNITY_TYPE.value: opportunity.opportunity_type.value,
        OpportunityEvidenceField.SOURCE_STATUS.value: _truncate(
            opportunity.source_status
        ),
    }
