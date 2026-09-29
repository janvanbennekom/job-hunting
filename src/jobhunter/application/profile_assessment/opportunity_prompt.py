"""Build opportunity text supplied to the assessment model."""

from __future__ import annotations

from jobhunter.domain.assessment_enums import OpportunityEvidenceField
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_structured_facts import OpportunityStructuredFacts
from jobhunter.domain.serialization import serialize_optional_date

_MAX_FIELD_LENGTH = 12_000


def _truncate(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if len(text) <= _MAX_FIELD_LENGTH:
        return text
    return text[:_MAX_FIELD_LENGTH]


def _join_labels(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else ""


def build_opportunity_prompt_text(
    opportunity: Opportunity,
    structured_facts: OpportunityStructuredFacts | None = None,
) -> dict[str, str]:
    facts = structured_facts or OpportunityStructuredFacts()
    publication = serialize_optional_date(opportunity.publication_date) or ""
    deadline = serialize_optional_date(opportunity.deadline) or ""
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
        OpportunityEvidenceField.PUBLICATION_DATE.value: publication,
        OpportunityEvidenceField.DEADLINE.value: deadline,
        OpportunityEvidenceField.ORGANISATION_TYPE.value: _truncate(
            facts.organisation_type
        ),
        OpportunityEvidenceField.CONTRACT_TYPE.value: _truncate(
            facts.contract_type_label
        ),
        OpportunityEvidenceField.MINIMUM_EXPERIENCE.value: (
            str(facts.minimum_experience_years)
            if facts.minimum_experience_years is not None
            else ""
        ),
        OpportunityEvidenceField.LANGUAGES.value: _truncate(
            _join_labels(facts.languages)
        ),
        OpportunityEvidenceField.SECTORS.value: _truncate(_join_labels(facts.sectors)),
        OpportunityEvidenceField.SALARY_SUMMARY.value: _truncate(
            facts.salary_summary
        ),
        OpportunityEvidenceField.CONTENT_LAST_UPDATED.value: _truncate(
            facts.content_last_updated
        ),
    }
