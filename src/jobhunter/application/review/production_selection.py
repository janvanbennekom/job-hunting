"""Select production-consistent assessments and rankings for dashboard reads."""

from __future__ import annotations

from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.opportunity_ranking import OpportunityRanking


def is_fake_assessment(assessment: OpportunityProfileAssessment | None) -> bool:
    return assessment is not None and assessment.model_provider == "fake"


def select_production_ranking(
    rankings_newest_first: list[OpportunityRanking],
    assessment_by_id: dict[str, OpportunityProfileAssessment],
    *,
    allow_fake: bool,
) -> OpportunityRanking | None:
    if allow_fake:
        return rankings_newest_first[0] if rankings_newest_first else None
    for ranking in rankings_newest_first:
        if ranking.profile_assessment_id is None:
            return ranking
        assessment = assessment_by_id.get(ranking.profile_assessment_id)
        if assessment is not None and assessment.model_provider == "fake":
            continue
        return ranking
    return None


def assessment_display_state(
    production: OpportunityProfileAssessment | None,
    latest_any: OpportunityProfileAssessment | None,
    *,
    allow_fake: bool,
):
    from jobhunter.application.review.dtos import AssessmentDisplayState
    from jobhunter.domain.assessment_enums import AssessmentStatus

    if production is not None:
        if production.status in (
            AssessmentStatus.FAILED_VALIDATION,
            AssessmentStatus.FAILED_PROVIDER,
        ):
            return AssessmentDisplayState.FAILED
        return AssessmentDisplayState.PRODUCTION
    if latest_any is None:
        return AssessmentDisplayState.NONE
    if is_fake_assessment(latest_any):
        if allow_fake:
            return AssessmentDisplayState.FAKE_DEV
        return AssessmentDisplayState.FAKE_ONLY
    return AssessmentDisplayState.NONE
