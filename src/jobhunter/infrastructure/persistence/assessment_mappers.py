"""Mappers for profile assessment persistence."""

from __future__ import annotations

from jobhunter.domain.assessment_enums import AssessmentStatus
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.infrastructure.persistence.models import OpportunityProfileAssessmentRow


def assessment_to_row(
    entity: OpportunityProfileAssessment,
) -> OpportunityProfileAssessmentRow:
    return OpportunityProfileAssessmentRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        search_strategy_revision_id=entity.search_strategy_revision_id,
        eligibility_decision_id=entity.eligibility_decision_id,
        assessed_at=entity.assessed_at,
        status=entity.status.value,
        input_digest=entity.input_digest,
        opportunity_content_digest=entity.opportunity_content_digest,
        profile_evidence_digest=entity.profile_evidence_digest,
        prompt_schema_version=entity.prompt_schema_version,
        model_provider=entity.model_provider,
        model_name=entity.model_name,
        validation_warnings=list(entity.validation_warnings),
        result=entity.result,
        provider_error=entity.provider_error,
    )


def assessment_to_domain(
    row: OpportunityProfileAssessmentRow,
) -> OpportunityProfileAssessment:
    warnings = row.validation_warnings or []
    return OpportunityProfileAssessment(
        id=row.id,
        opportunity_id=row.opportunity_id,
        search_strategy_revision_id=row.search_strategy_revision_id,
        eligibility_decision_id=row.eligibility_decision_id,
        assessed_at=row.assessed_at,
        status=AssessmentStatus(row.status),
        input_digest=row.input_digest,
        opportunity_content_digest=row.opportunity_content_digest,
        profile_evidence_digest=row.profile_evidence_digest,
        prompt_schema_version=row.prompt_schema_version,
        model_provider=row.model_provider,
        model_name=row.model_name,
        validation_warnings=[str(item) for item in warnings],
        result=row.result,
        provider_error=row.provider_error,
    )
