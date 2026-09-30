"""Opportunity queue queries for Phase 10 dashboard."""

from __future__ import annotations

from dataclasses import replace

from jobhunter.application.ranking.ordering import RankedOpportunityView, sort_ranked_views
from jobhunter.application.review.relevance_queue import (
    apply_hide_dismissed,
    count_segments,
    matches_relevance_queue,
    sort_queue_for_view,
)
from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
from jobhunter.application.review.dtos import (
    AssessmentDisplayState,
    OpportunityQueueFilters,
    OpportunityQueueItem,
)
from jobhunter.application.review.lifecycle import is_actionable_lifecycle
from jobhunter.application.review.opportunity_reads import (
    OpportunityPipelineReader,
    max_processed_at,
)
from jobhunter.application.review.source_links import pick_primary_source_link
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.ranking_enums import RankingStatus
from jobhunter.infrastructure.persistence.eligibility_repositories import (
    EligibilityDecisionRepository,
)
from jobhunter.infrastructure.persistence.repositories import (
    JobSourceRepository,
    OpportunityRepository,
    OpportunitySourceRepository,
)
from jobhunter.infrastructure.persistence.review_repositories import (
    OpportunityReviewRecordRepository,
)
from sqlalchemy.orm import Session


class OpportunityReviewQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._opportunities = OpportunityRepository(session)
        self._job_sources = JobSourceRepository(session)
        self._opp_sources = OpportunitySourceRepository(session)
        self._eligibility = EligibilityDecisionRepository(session)
        self._reviews = OpportunityReviewRecordRepository(session)
        self._strategy = ActiveSearchStrategyResolver(session)
        self._pipeline = OpportunityPipelineReader(session)

    def list_queue(
        self, filters: OpportunityQueueFilters | None = None
    ) -> list[OpportunityQueueItem]:
        resolved_filters = filters or OpportunityQueueFilters()
        ctx = self._strategy.resolve()
        revision_id = ctx.revision_id

        opportunities = self._opportunities.list_all()
        if resolved_filters.source_id:
            allowed = set(
                self._opportunities.list_ids_for_source(resolved_filters.source_id)
            )
            opportunities = [opp for opp in opportunities if opp.id in allowed]

        opp_ids = [opp.id for opp in opportunities]
        latest_reviews = self._reviews.map_latest_by_opportunity_ids(opp_ids)

        items: list[OpportunityQueueItem] = []
        for opp in opportunities:
            item = self._build_item(
                opp,
                revision_id,
                resolved_filters.allow_fake,
                latest_reviews.get(opp.id),
            )
            if self._matches_filters(opp, item, resolved_filters):
                items.append(item)

        items = apply_hide_dismissed(items, resolved_filters.hide_dismissed)
        items = self._order_queue(
            items, revision_id, resolved_filters.allow_fake, resolved_filters.relevance_queue
        )
        return sort_queue_for_view(items, resolved_filters.relevance_queue)

    def count_relevance_segments(
        self, filters: OpportunityQueueFilters | None = None
    ) -> dict[str, int]:
        """Counts per relevance segment for the same base filters (no segment/hide)."""
        base = filters or OpportunityQueueFilters()
        segment_filters = replace(
            base,
            relevance_queue=None,
            hide_dismissed=False,
        )
        items = self.list_queue(segment_filters)
        return count_segments(items)

    def _build_item(
        self,
        opp: Opportunity,
        revision_id: str,
        allow_fake: bool,
        review,
    ) -> OpportunityQueueItem:
        pipeline = self._pipeline.load(opp, revision_id, allow_fake=allow_fake)
        links = self._opp_sources.list_for_opportunity(opp.id)
        primary = pick_primary_source_link(links, self._job_sources)

        decision = self._eligibility.get_latest_for_opportunity_and_revision(
            opp.id, revision_id
        )
        ranking = pipeline.display_ranking
        assessment = pipeline.display_assessment

        overall = sufficiency = None
        if assessment and assessment.result:
            overall = assessment.result.get("overall_relevance")
            sufficiency = assessment.result.get("source_data_sufficiency")

        ranking_unavailable = None
        if (
            not allow_fake
            and pipeline.assessment_state is AssessmentDisplayState.FAKE_ONLY
        ):
            ranking_unavailable = "Production ranking unavailable (only dev/fake assessments exist)."

        return OpportunityQueueItem(
            opportunity_id=opp.id,
            title=opp.title,
            organisation=opp.organisation,
            location=opp.location,
            deadline=opp.deadline,
            lifecycle_status=opp.lifecycle_status,
            eligibility_status=opp.eligibility_status,
            source_id=primary.source_id if primary else None,
            source_name=primary.source_name if primary else None,
            external_url=primary.external_url if primary else None,
            dynamic_rank=None,
            ranking_status=ranking.status if ranking else None,
            priority_band=ranking.priority_band if ranking else None,
            overall_relevance=str(overall) if overall else None,
            source_data_sufficiency=str(sufficiency) if sufficiency else None,
            assessment_state=pipeline.assessment_state,
            unranked_reason=ranking.unranked_reason if ranking else None,
            exclusion_reason=ranking.exclusion_reason if ranking else None,
            last_seen_at=primary.last_seen_at if primary else None,
            last_processed_at=max_processed_at(
                decision.evaluated_at if decision else None,
                assessment.assessed_at if assessment else None,
                ranking.ranked_at if ranking else None,
            ),
            review_disposition=review.disposition if review else None,
            ranking_unavailable_reason=ranking_unavailable,
        )

    def _matches_filters(
        self,
        opp: Opportunity,
        item: OpportunityQueueItem,
        filters: OpportunityQueueFilters,
    ) -> bool:
        if not filters.include_non_actionable_lifecycle:
            if not is_actionable_lifecycle(opp.lifecycle_status):
                return False
        if not filters.include_ineligible:
            if opp.eligibility_status is not EligibilityStatus.ELIGIBLE:
                if filters.eligibility is None:
                    return False
        if filters.eligibility is not None:
            if opp.eligibility_status is not filters.eligibility:
                return False
        if filters.lifecycle is not None:
            if opp.lifecycle_status is not filters.lifecycle:
                return False
        if filters.assessment_state is not None:
            if item.assessment_state is not filters.assessment_state:
                return False
        if filters.location_contains:
            needle = filters.location_contains.strip().lower()
            hay = (opp.location or "").lower()
            if needle and needle not in hay:
                return False
        if filters.review_disposition is not None:
            if item.review_disposition is not filters.review_disposition:
                return False
        if filters.ranking_band is not None:
            if item.priority_band is not filters.ranking_band:
                return False
        if not matches_relevance_queue(item, filters.relevance_queue):
            return False
        return True

    def _order_queue(
        self,
        items: list[OpportunityQueueItem],
        revision_id: str,
        allow_fake: bool,
        relevance_queue,
    ) -> list[OpportunityQueueItem]:
        ranked_views: list[RankedOpportunityView] = []
        for item in items:
            if item.ranking_status is not RankingStatus.RANKED:
                continue
            opp = self._opportunities.get_by_id(item.opportunity_id)
            if opp is None:
                continue
            ranking = self._pipeline.load(
                opp, revision_id, allow_fake=allow_fake
            ).display_ranking
            if ranking is None or ranking.status is not RankingStatus.RANKED:
                continue
            ranked_views.append(RankedOpportunityView(opportunity=opp, ranking=ranking))

        sorted_ranked = sort_ranked_views(ranked_views)
        rank_map = {
            view.opportunity.id: index
            for index, view in enumerate(sorted_ranked, start=1)
        }

        enriched = [
            replace(item, dynamic_rank=rank_map.get(item.opportunity_id))
            for item in items
        ]

        def sort_key(row: OpportunityQueueItem) -> tuple:
            if row.dynamic_rank is not None:
                return (0, row.dynamic_rank, row.title)
            if row.eligibility_status is EligibilityStatus.ELIGIBLE:
                return (1, str(row.deadline or ""), row.title)
            return (2, row.title)

        return sorted(enriched, key=sort_key)
