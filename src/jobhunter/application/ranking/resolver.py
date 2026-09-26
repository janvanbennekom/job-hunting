"""Resolve ranking inputs from persistence."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from jobhunter.application.profile_assessment.digests import (
    compute_opportunity_content_digest,
)
from jobhunter.application.ranking.inputs import RankingResolvedInputs
from jobhunter.domain.eligibility_decision import EligibilityDecision
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.ranking_enums import UnrankedReason
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.eligibility_repositories import (
    EligibilityDecisionRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.infrastructure.persistence.strategy_repositories import (
    PersistedRevisionSnapshot,
)


@dataclass(frozen=True, slots=True)
class RankingResolveFailure:
    reason: UnrankedReason
    eligibility: EligibilityDecision | None
    assessment: OpportunityProfileAssessment | None


class RankingInputResolver:
    def __init__(self, session: Session) -> None:
        self._opportunities = OpportunityRepository(session)
        self._eligibility = EligibilityDecisionRepository(session)
        self._assessments = OpportunityProfileAssessmentRepository(session)

    def resolve(
        self,
        opportunity_id: str,
        snapshot: PersistedRevisionSnapshot,
        *,
        include_fake_assessments: bool = False,
    ) -> RankingResolvedInputs | RankingResolveFailure:
        opportunity = self._opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        revision_id = snapshot.revision.id
        eligibility = self._eligibility.get_latest_for_opportunity_and_revision(
            opportunity_id, revision_id
        )
        if eligibility is None:
            return RankingResolveFailure(
                UnrankedReason.ELIGIBILITY_REVISION_MISMATCH,
                None,
                None,
            )

        assessment = self._assessments.get_latest_success_for_revision(
            opportunity_id,
            revision_id,
            allow_fake=include_fake_assessments,
        )
        if assessment is None:
            return RankingResolveFailure(
                UnrankedReason.MISSING_ASSESSMENT,
                eligibility,
                None,
            )

        return RankingResolvedInputs(
            opportunity=opportunity,
            snapshot=snapshot,
            eligibility=eligibility,
            assessment=assessment,
            opportunity_content_digest=compute_opportunity_content_digest(opportunity),
            include_fake_assessments=include_fake_assessments,
        )
