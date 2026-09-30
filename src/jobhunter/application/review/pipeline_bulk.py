"""Bulk pipeline index for active search strategy revision (Phase 17H-1)."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from jobhunter.application.review.pipeline_assembly import (
    AssembledPipelineState,
    assemble_pipeline_state,
)
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.opportunity_ranking import OpportunityRanking
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.ranking_repositories import (
    OpportunityRankingRepository,
)


class OpportunityPipelineBulkIndex:
    """Per-opportunity pipeline state from a fixed number of revision-wide SELECTs."""

    def __init__(
        self,
        revision_id: str,
        states: dict[str, AssembledPipelineState],
        assessment_by_id: dict[str, OpportunityProfileAssessment],
    ) -> None:
        self.revision_id = revision_id
        self._states = states
        self.assessment_by_id = assessment_by_id

    def get(self, opportunity_id: str) -> AssembledPipelineState:
        return self._states.get(opportunity_id) or _empty_state()

    @classmethod
    def load(
        cls,
        session: Session,
        revision_id: str,
        *,
        allow_fake: bool,
    ) -> OpportunityPipelineBulkIndex:
        assessments = OpportunityProfileAssessmentRepository(session).list_for_revision(
            revision_id
        )
        rankings = OpportunityRankingRepository(session).list_for_revision(revision_id)
        assessment_by_id = {row.id: row for row in assessments if row.id}

        assessments_by_opp: dict[str, list[OpportunityProfileAssessment]] = defaultdict(
            list
        )
        for row in assessments:
            assessments_by_opp[row.opportunity_id].append(row)
        for rows in assessments_by_opp.values():
            rows.sort(key=lambda item: item.assessed_at)

        rankings_by_opp: dict[str, list[OpportunityRanking]] = defaultdict(list)
        for row in rankings:
            rankings_by_opp[row.opportunity_id].append(row)
        for rows in rankings_by_opp.values():
            rows.sort(key=lambda item: item.ranked_at, reverse=True)

        opportunity_ids = set(assessments_by_opp) | set(rankings_by_opp)
        states: dict[str, AssembledPipelineState] = {}
        for opportunity_id in opportunity_ids:
            states[opportunity_id] = assemble_pipeline_state(
                assessments_by_opp.get(opportunity_id, []),
                rankings_by_opp.get(opportunity_id, []),
                assessment_by_id,
                allow_fake=allow_fake,
            )

        return cls(revision_id, states, assessment_by_id)


def _empty_state() -> AssembledPipelineState:
    from jobhunter.application.review.dtos import AssessmentDisplayState

    return AssembledPipelineState(
        production=None,
        latest_any=None,
        display_assessment=None,
        display_ranking=None,
        assessment_state=AssessmentDisplayState.NONE,
    )
