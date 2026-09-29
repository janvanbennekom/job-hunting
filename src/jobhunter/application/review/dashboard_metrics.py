"""Bulk dashboard metric helpers (avoid per-opportunity pipeline N+1 queries)."""

from __future__ import annotations

from collections import Counter, defaultdict

from jobhunter.application.review.dtos import AssessmentDisplayState
from jobhunter.application.review.production_selection import (
    assessment_display_state,
    select_production_ranking,
)
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.opportunity_ranking import OpportunityRanking
from jobhunter.domain.ranking_enums import RankingStatus


def compute_production_dashboard_counts(
    assessments: list[OpportunityProfileAssessment],
    rankings: list[OpportunityRanking],
    *,
    allow_fake: bool,
) -> tuple[int, int, Counter[str]]:
    """Return (production_assessed, production_ranked, by_priority_band)."""
    assessments_by_opp: dict[str, list[OpportunityProfileAssessment]] = defaultdict(list)
    for row in assessments:
        assessments_by_opp[row.opportunity_id].append(row)

    rankings_by_opp: dict[str, list[OpportunityRanking]] = defaultdict(list)
    for row in rankings:
        rankings_by_opp[row.opportunity_id].append(row)

    assessment_by_id = {row.id: row for row in assessments if row.id}

    production_assessed = 0
    production_ranked = 0
    by_band: Counter[str] = Counter()

    opportunity_ids = set(assessments_by_opp) | set(rankings_by_opp)
    for opportunity_id in opportunity_ids:
        opp_assessments = sorted(
            assessments_by_opp.get(opportunity_id, []),
            key=lambda item: item.assessed_at,
        )
        production = _latest_success_non_fake(opp_assessments, allow_fake=allow_fake)
        latest_any = opp_assessments[-1] if opp_assessments else None
        state = assessment_display_state(production, latest_any, allow_fake=allow_fake)

        if allow_fake:
            if state in (
                AssessmentDisplayState.PRODUCTION,
                AssessmentDisplayState.FAKE_DEV,
            ):
                production_assessed += 1
        elif state is AssessmentDisplayState.PRODUCTION:
            production_assessed += 1

        opp_rankings = sorted(
            rankings_by_opp.get(opportunity_id, []),
            key=lambda item: item.ranked_at,
            reverse=True,
        )
        display_ranking = select_production_ranking(
            opp_rankings, assessment_by_id, allow_fake=allow_fake
        )
        if display_ranking and display_ranking.status is RankingStatus.RANKED:
            if allow_fake or state is AssessmentDisplayState.PRODUCTION:
                production_ranked += 1
                if display_ranking.priority_band:
                    by_band[display_ranking.priority_band.value] += 1

    return production_assessed, production_ranked, by_band


def _latest_success_non_fake(
    assessments_chronological: list[OpportunityProfileAssessment],
    *,
    allow_fake: bool,
) -> OpportunityProfileAssessment | None:
    from jobhunter.domain.assessment_enums import AssessmentStatus

    for row in reversed(assessments_chronological):
        if row.status not in (
            AssessmentStatus.SUCCEEDED,
            AssessmentStatus.SUCCEEDED_WITH_WARNINGS,
        ):
            continue
        if row.model_provider == "fake" and not allow_fake:
            continue
        return row
    return None
