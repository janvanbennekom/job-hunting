"""Shared read helpers for opportunity dashboard context."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from jobhunter.application.review.dtos import AssessmentDisplayState
from jobhunter.application.review.production_selection import (
    assessment_display_state,
    select_production_ranking,
)
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.opportunity_ranking import OpportunityRanking
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.ranking_repositories import (
    OpportunityRankingRepository,
)


class OpportunityPipelineReadModel:
    def __init__(
        self,
        display_assessment: OpportunityProfileAssessment | None,
        latest_assessment: OpportunityProfileAssessment | None,
        display_ranking: OpportunityRanking | None,
        assessment_state: AssessmentDisplayState,
    ) -> None:
        self.display_assessment = display_assessment
        self.latest_assessment = latest_assessment
        self.display_ranking = display_ranking
        self.assessment_state = assessment_state


class OpportunityPipelineReader:
    def __init__(self, session: Session) -> None:
        self._assessments = OpportunityProfileAssessmentRepository(session)
        self._rankings = OpportunityRankingRepository(session)

    def load(
        self,
        opportunity: Opportunity,
        revision_id: str,
        *,
        allow_fake: bool,
    ) -> OpportunityPipelineReadModel:
        production = self._assessments.get_latest_success_for_revision(
            opportunity.id,
            revision_id,
            allow_fake=False,
        )
        latest = self._latest_assessment_any(opportunity.id, revision_id)
        display_assessment = self._assessments.get_latest_success_for_revision(
            opportunity.id,
            revision_id,
            allow_fake=allow_fake,
        )

        rankings = self._rankings.list_for_opportunity_and_revision(
            opportunity.id, revision_id
        )
        assessment_by_id = self._load_assessments_for_rankings(rankings)
        display_ranking = select_production_ranking(
            rankings, assessment_by_id, allow_fake=allow_fake
        )

        state = assessment_display_state(production, latest, allow_fake=allow_fake)

        return OpportunityPipelineReadModel(
            display_assessment=display_assessment,
            latest_assessment=latest,
            display_ranking=display_ranking,
            assessment_state=state,
        )

    def _latest_assessment_any(
        self, opportunity_id: str, revision_id: str
    ) -> OpportunityProfileAssessment | None:
        rows = [
            row
            for row in self._assessments.list_for_opportunity(opportunity_id)
            if row.search_strategy_revision_id == revision_id
        ]
        return rows[-1] if rows else None

    def _load_assessments_for_rankings(
        self, rankings: list[OpportunityRanking]
    ) -> dict[str, OpportunityProfileAssessment]:
        result: dict[str, OpportunityProfileAssessment] = {}
        for ranking in rankings:
            aid = ranking.profile_assessment_id
            if aid and aid not in result:
                entity = self._assessments.get_by_id(aid)
                if entity:
                    result[aid] = entity
        return result


def max_processed_at(
    eligibility_at: datetime | None,
    assessment_at: datetime | None,
    ranking_at: datetime | None,
) -> datetime | None:
    values = [v for v in (eligibility_at, assessment_at, ranking_at) if v is not None]
    return max(values) if values else None
