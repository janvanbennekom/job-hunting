"""Append-only human review records."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
from jobhunter.application.review.opportunity_reads import OpportunityPipelineReader
from jobhunter.domain.opportunity_review_record import OpportunityReviewRecord
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.infrastructure.persistence.review_repositories import (
    OpportunityReviewRecordRepository,
)


class HumanReviewService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._opportunities = OpportunityRepository(session)
        self._reviews = OpportunityReviewRecordRepository(session)
        self._strategy = ActiveSearchStrategyResolver(session)
        self._pipeline = OpportunityPipelineReader(session)

    def append_review(
        self,
        opportunity_id: str,
        disposition: ReviewDisposition,
        notes: str | None = None,
        *,
        recorded_at: datetime | None = None,
    ) -> OpportunityReviewRecord:
        if self._opportunities.get_by_id(opportunity_id) is None:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        ctx = self._strategy.resolve()
        opp = self._opportunities.get_by_id(opportunity_id)
        assert opp is not None
        pipeline = self._pipeline.load(
            opp, ctx.revision_id, allow_fake=False
        )
        ranking = pipeline.display_ranking
        assessment = pipeline.display_assessment

        record = OpportunityReviewRecord(
            opportunity_id=opportunity_id,
            recorded_at=recorded_at or datetime.now(timezone.utc),
            disposition=disposition,
            notes=notes.strip() if notes and notes.strip() else None,
            search_strategy_revision_id=ctx.revision_id,
            profile_assessment_id=assessment.id if assessment else None,
            ranking_id=ranking.id if ranking else None,
        )
        return self._reviews.save(record)

    def get_latest(self, opportunity_id: str) -> OpportunityReviewRecord | None:
        return self._reviews.get_latest_for_opportunity(opportunity_id)

    def list_history(self, opportunity_id: str) -> list[OpportunityReviewRecord]:
        return self._reviews.list_for_opportunity(opportunity_id)
