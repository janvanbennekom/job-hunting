"""Dashboard home summary (read-only)."""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
from jobhunter.application.review.dtos import (
    AssessmentDisplayState,
    DashboardSummaryView,
    OpportunityQueueFilters,
    ScanSummaryView,
)
from jobhunter.application.review.lifecycle import is_actionable_lifecycle
from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService
from jobhunter.application.review.opportunity_reads import OpportunityPipelineReader
from jobhunter.domain.enums import EligibilityStatus
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.infrastructure.persistence.repositories import (
    JobSourceRepository,
    OpportunityRepository,
)
from jobhunter.infrastructure.persistence.source_scan_repository import SourceScanRepository


class DashboardSummaryService:
    DEFAULT_SOURCE_ID = "fao-external-jobs"

    def __init__(self, session: Session) -> None:
        self._session = session
        self._opportunities = OpportunityRepository(session)
        self._sources = JobSourceRepository(session)
        self._scans = SourceScanRepository(session)
        self._strategy = ActiveSearchStrategyResolver(session)
        self._pipeline = OpportunityPipelineReader(session)
        self._queue = OpportunityReviewQueryService(session)

    def build_summary(
        self,
        *,
        source_id: str | None = None,
        allow_fake: bool = False,
    ) -> DashboardSummaryView:
        resolved_source = source_id or self.DEFAULT_SOURCE_ID
        ctx = self._strategy.resolve()
        revision_id = ctx.revision_id

        opportunities = self._opportunities.list_all()
        by_lifecycle = Counter(opp.lifecycle_status.value for opp in opportunities)
        by_eligibility = Counter(opp.eligibility_status.value for opp in opportunities)

        actionable = sum(
            1
            for opp in opportunities
            if is_actionable_lifecycle(opp.lifecycle_status)
            and opp.eligibility_status is EligibilityStatus.ELIGIBLE
        )

        production_assessed = 0
        production_ranked = 0
        by_band: Counter[str] = Counter()

        for opp in opportunities:
            pipeline = self._pipeline.load(
                opp, revision_id, allow_fake=allow_fake
            )
            if allow_fake:
                if pipeline.assessment_state in (
                    AssessmentDisplayState.PRODUCTION,
                    AssessmentDisplayState.FAKE_DEV,
                ):
                    production_assessed += 1
            elif pipeline.assessment_state is AssessmentDisplayState.PRODUCTION:
                production_assessed += 1

            ranking = pipeline.display_ranking
            if ranking and ranking.status is RankingStatus.RANKED:
                if allow_fake or pipeline.assessment_state is AssessmentDisplayState.PRODUCTION:
                    production_ranked += 1
                    if ranking.priority_band:
                        by_band[ranking.priority_band.value] += 1

        latest_scan_entity = self._scans.get_latest_for_source(resolved_source)
        job_source = self._sources.get_by_id(resolved_source)
        scan_view = None
        if latest_scan_entity:
            scan_view = ScanSummaryView(
                source_id=resolved_source,
                source_name=job_source.name if job_source else resolved_source,
                scan_id=latest_scan_entity.id,
                status=latest_scan_entity.status.value,
                started_at=latest_scan_entity.started_at,
                completed_at=latest_scan_entity.completed_at,
                records_retrieved=latest_scan_entity.records_retrieved,
                records_processed=latest_scan_entity.records_processed,
                records_failed=latest_scan_entity.records_failed,
                error_summary=latest_scan_entity.error_summary,
            )

        preview_filters = OpportunityQueueFilters(
            allow_fake=allow_fake,
            include_ineligible=False,
            include_non_actionable_lifecycle=False,
            ranking_band=PriorityBand.HIGH,
        )
        high_preview = self._queue.list_queue(preview_filters)

        return DashboardSummaryView(
            total_opportunities=len(opportunities),
            by_lifecycle=dict(by_lifecycle),
            by_eligibility=dict(by_eligibility),
            actionable_count=actionable,
            production_assessed_count=production_assessed,
            production_ranked_count=production_ranked,
            by_ranking_band=dict(by_band),
            latest_scan=scan_view,
            high_priority_preview=high_preview[:5],
        )
