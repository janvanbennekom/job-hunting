"""Opportunity queue queries for Phase 10 dashboard."""

from __future__ import annotations

from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
from jobhunter.application.review.dtos import OpportunityQueueFilters, OpportunityQueueItem
from jobhunter.application.review.queue_snapshot import OpportunityQueueSnapshot
from sqlalchemy.orm import Session


class OpportunityReviewQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._strategy = ActiveSearchStrategyResolver(session)

    def build_snapshot(
        self, base_filters: OpportunityQueueFilters | None = None
    ) -> OpportunityQueueSnapshot:
        return OpportunityQueueSnapshot.build(
            self._session, base_filters or OpportunityQueueFilters()
        )

    def list_queue(
        self, filters: OpportunityQueueFilters | None = None
    ) -> list[OpportunityQueueItem]:
        resolved = filters or OpportunityQueueFilters()
        snapshot = self.build_snapshot(resolved)
        return snapshot.list_queue(resolved)

    def count_relevance_segments(
        self, filters: OpportunityQueueFilters | None = None
    ) -> dict[str, int]:
        base = filters or OpportunityQueueFilters()
        snapshot = self.build_snapshot(base)
        return snapshot.segment_counts(base)

    def list_queue_with_snapshot(
        self,
        base_filters: OpportunityQueueFilters,
        display_filters: OpportunityQueueFilters,
    ) -> tuple[OpportunityQueueSnapshot, dict[str, int], list[OpportunityQueueItem]]:
        """One bulk load for segment counts and displayed queue (Opportunities page)."""
        snapshot = self.build_snapshot(base_filters)
        counts = snapshot.segment_counts(base_filters)
        items = snapshot.list_queue(display_filters)
        return snapshot, counts, items

    def get_dynamic_rank(
        self, opportunity_id: str, *, allow_fake: bool = False
    ) -> int | None:
        base = OpportunityQueueFilters(allow_fake=allow_fake)
        snapshot = self.build_snapshot(base)
        return snapshot.dynamic_rank_for(opportunity_id, allow_fake=allow_fake)
