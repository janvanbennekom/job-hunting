"""Assemble per-opportunity pipeline state from bulk-loaded revision data."""

from __future__ import annotations

from dataclasses import dataclass

from jobhunter.application.review.dtos import AssessmentDisplayState
from jobhunter.application.review.production_selection import (
    assessment_display_state,
    select_production_ranking,
)
from jobhunter.domain.assessment_enums import AssessmentStatus
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.opportunity_ranking import OpportunityRanking

_SUCCESS_STATUSES = frozenset(
    {
        AssessmentStatus.SUCCEEDED,
        AssessmentStatus.SUCCEEDED_WITH_WARNINGS,
    }
)


@dataclass(frozen=True, slots=True)
class AssembledPipelineState:
    production: OpportunityProfileAssessment | None
    latest_any: OpportunityProfileAssessment | None
    display_assessment: OpportunityProfileAssessment | None
    display_ranking: OpportunityRanking | None
    assessment_state: AssessmentDisplayState


def assemble_pipeline_state(
    assessments_for_revision_chronological: list[OpportunityProfileAssessment],
    rankings_newest_first: list[OpportunityRanking],
    assessment_by_id: dict[str, OpportunityProfileAssessment],
    *,
    allow_fake: bool,
) -> AssembledPipelineState:
    production = _latest_success(assessments_for_revision_chronological, allow_fake=False)
    latest_any = (
        assessments_for_revision_chronological[-1]
        if assessments_for_revision_chronological
        else None
    )
    display_assessment = _latest_success(
        assessments_for_revision_chronological, allow_fake=allow_fake
    )
    display_ranking = select_production_ranking(
        rankings_newest_first, assessment_by_id, allow_fake=allow_fake
    )
    state = assessment_display_state(production, latest_any, allow_fake=allow_fake)
    return AssembledPipelineState(
        production=production,
        latest_any=latest_any,
        display_assessment=display_assessment,
        display_ranking=display_ranking,
        assessment_state=state,
    )


def _latest_success(
    assessments_chronological: list[OpportunityProfileAssessment],
    *,
    allow_fake: bool,
) -> OpportunityProfileAssessment | None:
    for row in reversed(assessments_chronological):
        if row.status not in _SUCCESS_STATUSES:
            continue
        if row.model_provider == "fake" and not allow_fake:
            continue
        return row
    return None
