"""Single-pass opportunity queue snapshot (Phase 17H-1)."""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy.orm import Session

from jobhunter.application.ranking.ordering import RankedOpportunityView, sort_ranked_views
from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
from jobhunter.application.review.dtos import (
    AssessmentDisplayState,
    OpportunityQueueFilters,
    OpportunityQueueItem,
)
from jobhunter.application.review.lifecycle import is_actionable_lifecycle
from jobhunter.application.review.opportunity_reads import max_processed_at
from jobhunter.application.review.pipeline_bulk import OpportunityPipelineBulkIndex
from jobhunter.application.review.relevance_queue import (
    apply_hide_dismissed,
    count_segments,
    matches_relevance_queue,
    sort_queue_for_view,
)
from jobhunter.application.review.source_links import pick_primary_source_link
from jobhunter.domain.enums import EligibilityStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_review_record import OpportunityReviewRecord
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


class OpportunityQueueSnapshot:
    """Bulk-loaded queue state; segment counts and filtered lists share one load."""

    def __init__(
        self,
        revision_id: str,
        allow_fake: bool,
        opportunities: list[Opportunity],
        opportunities_by_id: dict[str, Opportunity],
        pipeline: OpportunityPipelineBulkIndex,
        eligibility_by_opp: dict,
        sources_by_opp: dict,
        job_sources: dict,
        reviews_by_opp: dict[str, OpportunityReviewRecord],
    ) -> None:
        self.revision_id = revision_id
        self.allow_fake = allow_fake
        self._opportunities = opportunities
        self._opportunities_by_id = opportunities_by_id
        self._pipeline = pipeline
        self._eligibility_by_opp = eligibility_by_opp
        self._sources_by_opp = sources_by_opp
        self._job_sources = job_sources
        self._reviews_by_opp = reviews_by_opp

    @classmethod
    def build(
        cls,
        session: Session,
        base_filters: OpportunityQueueFilters,
    ) -> OpportunityQueueSnapshot:
        strategy = ActiveSearchStrategyResolver(session)
        ctx = strategy.resolve()
        revision_id = ctx.revision_id

        opportunities = OpportunityRepository(session).list_all()
        if base_filters.source_id:
            allowed = set(
                OpportunityRepository(session).list_ids_for_source(
                    base_filters.source_id
                )
            )
            opportunities = [opp for opp in opportunities if opp.id in allowed]

        opp_ids = [opp.id for opp in opportunities]
        pipeline = OpportunityPipelineBulkIndex.load(
            session, revision_id, allow_fake=base_filters.allow_fake
        )
        eligibility_by_opp = EligibilityDecisionRepository(
            session
        ).map_latest_for_revision(revision_id)
        sources_by_opp = OpportunitySourceRepository(
            session
        ).map_all_grouped_by_opportunity()
        job_sources = JobSourceRepository(session).map_all_by_id()
        reviews_by_opp = OpportunityReviewRecordRepository(
            session
        ).map_latest_by_opportunity_ids(opp_ids)

        return cls(
            revision_id,
            base_filters.allow_fake,
            opportunities,
            {opp.id: opp for opp in opportunities},
            pipeline,
            eligibility_by_opp,
            sources_by_opp,
            job_sources,
            reviews_by_opp,
        )

    def segment_counts(self, base_filters: OpportunityQueueFilters) -> dict[str, int]:
        filters = replace(
            base_filters,
            relevance_queue=None,
            hide_dismissed=False,
        )
        items = self._collect_items(filters)
        return count_segments(items)

    def list_queue(self, filters: OpportunityQueueFilters) -> list[OpportunityQueueItem]:
        items = self._collect_items(filters)
        items = apply_hide_dismissed(items, filters.hide_dismissed)
        items = self._order_items(items)
        return sort_queue_for_view(items, filters.relevance_queue)

    @property
    def pipeline_index(self) -> OpportunityPipelineBulkIndex:
        return self._pipeline

    def dynamic_rank_for(
        self, opportunity_id: str, *, allow_fake: bool
    ) -> int | None:
        filters = OpportunityQueueFilters(allow_fake=allow_fake)
        items = self._collect_items(filters)
        items = self._order_items(items)
        for item in items:
            if item.opportunity_id == opportunity_id:
                return item.dynamic_rank
        return None

    def _collect_items(self, filters: OpportunityQueueFilters) -> list[OpportunityQueueItem]:
        items: list[OpportunityQueueItem] = []
        for opp in self._opportunities:
            if not self._matches_opportunity_cheap(opp, filters):
                continue
            review = self._reviews_by_opp.get(opp.id)
            if filters.review_disposition is not None:
                disp = review.disposition if review else None
                if disp is not filters.review_disposition:
                    continue
            pipeline_state = self._pipeline.get(opp.id)
            if filters.assessment_state is not None:
                if pipeline_state.assessment_state is not filters.assessment_state:
                    continue
            ranking = pipeline_state.display_ranking
            if filters.ranking_band is not None:
                band = ranking.priority_band if ranking else None
                if band is not filters.ranking_band:
                    continue
            item = self._build_item(opp, pipeline_state, review)
            if not matches_relevance_queue(item, filters.relevance_queue):
                continue
            items.append(item)
        return items

    def _matches_opportunity_cheap(
        self, opp: Opportunity, filters: OpportunityQueueFilters
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
        if filters.location_contains:
            needle = filters.location_contains.strip().lower()
            hay = (opp.location or "").lower()
            if needle and needle not in hay:
                return False
        return True

    def _build_item(self, opp, pipeline_state, review) -> OpportunityQueueItem:
        links = self._sources_by_opp.get(opp.id, [])
        primary = pick_primary_source_link(links, self._job_sources)
        decision = self._eligibility_by_opp.get(opp.id)
        ranking = pipeline_state.display_ranking
        assessment = pipeline_state.display_assessment

        overall = sufficiency = None
        if assessment and assessment.result:
            overall = assessment.result.get("overall_relevance")
            sufficiency = assessment.result.get("source_data_sufficiency")

        ranking_unavailable = None
        if (
            not self.allow_fake
            and pipeline_state.assessment_state is AssessmentDisplayState.FAKE_ONLY
        ):
            ranking_unavailable = (
                "Production ranking unavailable (only dev/fake assessments exist)."
            )

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
            assessment_state=pipeline_state.assessment_state,
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

    def _order_items(self, items: list[OpportunityQueueItem]) -> list[OpportunityQueueItem]:
        ranked_views: list[RankedOpportunityView] = []
        for item in items:
            if item.ranking_status is not RankingStatus.RANKED:
                continue
            opp = self._opportunities_by_id.get(item.opportunity_id)
            if opp is None:
                continue
            ranking = self._pipeline.get(item.opportunity_id).display_ranking
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
