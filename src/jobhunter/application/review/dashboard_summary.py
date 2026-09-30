"""Dashboard home summary (read-only)."""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
from jobhunter.application.review.dtos import (
    DashboardSummaryView,
    OpportunityQueueFilters,
    ScanSummaryView,
)
from jobhunter.application.review.lifecycle import is_actionable_lifecycle
from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService
from jobhunter.application.review.dashboard_metrics import (
    compute_production_dashboard_counts,
)
from jobhunter.domain.enums import EligibilityStatus
from jobhunter.domain.ranking_enums import PriorityBand
from jobhunter.domain.relevance_queue_enums import RelevanceQueueView
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.ranking_repositories import (
    OpportunityRankingRepository,
)
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
        self._assessments = OpportunityProfileAssessmentRepository(session)
        self._rankings = OpportunityRankingRepository(session)
        self._queue = OpportunityReviewQueryService(session)

    def build_summary(
        self,
        *,
        source_id: str | None = None,
        allow_fake: bool = False,
        include_queue_preview: bool = True,
        include_latest_scan: bool = True,
        include_relevance_counts: bool = True,
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

        revision_assessments = self._assessments.list_for_revision(revision_id)
        revision_rankings = self._rankings.list_for_revision(revision_id)
        production_assessed, production_ranked, by_band = (
            compute_production_dashboard_counts(
                revision_assessments,
                revision_rankings,
                allow_fake=allow_fake,
            )
        )

        scan_view = None
        if include_latest_scan:
            latest_scan_entity = self._scans.get_latest_for_source(resolved_source)
            job_source = self._sources.get_by_id(resolved_source)
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

        base_queue_filters = OpportunityQueueFilters(
            allow_fake=allow_fake,
            include_ineligible=False,
            include_non_actionable_lifecycle=False,
        )
        snapshot = None
        if include_queue_preview or include_relevance_counts:
            snapshot = self._queue.build_snapshot(base_queue_filters)

        high_preview = []
        if include_queue_preview and snapshot is not None:
            preview_filters = OpportunityQueueFilters(
                allow_fake=allow_fake,
                include_ineligible=False,
                include_non_actionable_lifecycle=False,
                ranking_band=PriorityBand.HIGH,
            )
            high_preview = snapshot.list_queue(preview_filters)

        relevance_counts: dict[str, int] = {}
        if include_relevance_counts and snapshot is not None:
            relevance_counts = snapshot.segment_counts(base_queue_filters)

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
            by_relevance_queue={
                RelevanceQueueView.PRIMARY.value: relevance_counts.get(
                    RelevanceQueueView.PRIMARY.value, 0
                ),
                RelevanceQueueView.WEAK.value: relevance_counts.get(
                    RelevanceQueueView.WEAK.value, 0
                ),
                RelevanceQueueView.OUT_OF_SCOPE.value: relevance_counts.get(
                    RelevanceQueueView.OUT_OF_SCOPE.value, 0
                ),
            },
        )
