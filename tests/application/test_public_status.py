"""Public aggregate status page."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.review.dashboard_summary import DashboardSummaryService
from jobhunter.application.review.dtos import DashboardSummaryView
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.ui.public_status.html import render_public_status_html

pytestmark = pytest.mark.integration


def test_public_html_uses_dashboard_summary_metrics(db_session: Session) -> None:
    OpportunityRepository(db_session).save(
        Opportunity(
            id="pub-opp-1",
            title="Secret GIS Consultant Title",
            organisation="Secret Client Org",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    summary = DashboardSummaryService(db_session).build_summary(allow_fake=False)
    html = render_public_status_html(summary)
    assert "Secret GIS Consultant Title" not in html
    assert "Secret Client Org" not in html
    assert "pub-opp-1" not in html
    assert str(summary.total_opportunities) in html
    assert "Lifecycle" in html
    assert "Eligibility" in html


def test_public_server_rejects_unknown_paths() -> None:
    from jobhunter.ui.public_status.server import application

    status: list[str] = []
    body = b"".join(
        application(
            {"PATH_INFO": "/app/opportunities"},
            lambda code, headers: status.append(code),
        )
    )
    assert status[0].startswith("404")
    assert body == b"Not Found"


def test_health_returns_ok_without_dashboard_service() -> None:
    from jobhunter.ui.public_status.server import application

    status: list[str] = []
    with patch(
        "jobhunter.ui.public_status.server.DashboardSummaryService",
        MagicMock(),
    ) as mock_cls:
        body = b"".join(
            application(
                {"PATH_INFO": "/health"},
                lambda code, headers: status.append(code),
            )
        )
        mock_cls.assert_not_called()
    assert status[0].startswith("200")
    assert body == b"OK"


def test_status_invokes_dashboard_with_public_flags() -> None:
    from jobhunter.ui.public_status.server import application

    empty_summary = DashboardSummaryView(
        total_opportunities=0,
        by_lifecycle={},
        by_eligibility={},
        actionable_count=0,
        production_assessed_count=0,
        production_ranked_count=0,
        by_ranking_band={},
        latest_scan=None,
        high_priority_preview=[],
    )
    status: list[str] = []
    with patch(
        "jobhunter.ui.public_status.server._session_factory_singleton",
        return_value=MagicMock(),
    ):
        with patch("jobhunter.ui.public_status.server.session_scope") as scope_ctx:
            scope_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
            scope_ctx.return_value.__exit__ = MagicMock(return_value=False)
            with patch(
                "jobhunter.ui.public_status.server.DashboardSummaryService"
            ) as mock_cls:
                mock_cls.return_value.build_summary.return_value = empty_summary
                body = b"".join(
                    application(
                        {"PATH_INFO": "/status"},
                        lambda code, headers: status.append(code),
                    )
                )
                mock_cls.return_value.build_summary.assert_called_once_with(
                    allow_fake=False,
                    include_queue_preview=False,
                    include_latest_scan=False,
                    include_relevance_counts=False,
                )
    assert status[0].startswith("200")
    assert b"Lifecycle" in body


def test_build_summary_public_flags_skip_queue_and_scan(db_session: Session) -> None:
    from jobhunter.application.review.opportunity_query import (
        OpportunityReviewQueryService,
    )
    from jobhunter.infrastructure.persistence.source_scan_repository import (
        SourceScanRepository,
    )

    with patch.object(
        OpportunityReviewQueryService, "list_queue", return_value=[]
    ) as list_queue:
        with patch.object(
            SourceScanRepository, "get_latest_for_source", return_value=None
        ) as latest_scan:
            DashboardSummaryService(db_session).build_summary(
                allow_fake=False,
                include_queue_preview=False,
                include_latest_scan=False,
                include_relevance_counts=False,
            )
            list_queue.assert_not_called()
            latest_scan.assert_not_called()


def test_dashboard_bulk_metrics_match_pipeline_for_sample(
    db_session: Session,
) -> None:
    """Bulk path should match per-opportunity pipeline for production counts."""
    from jobhunter.application.review.active_strategy import (
        ActiveSearchStrategyResolver,
    )
    from jobhunter.application.review.opportunity_reads import (
        OpportunityPipelineReader,
    )
    from jobhunter.domain.ranking_enums import RankingStatus

    opportunities = OpportunityRepository(db_session).list_all()
    ctx = ActiveSearchStrategyResolver(db_session).resolve()
    revision_id = ctx.revision_id
    pipeline = OpportunityPipelineReader(db_session)

    from jobhunter.application.review.dtos import AssessmentDisplayState

    pipeline_assessed = 0
    pipeline_ranked = 0
    for opp in opportunities:
        loaded = pipeline.load(opp, revision_id, allow_fake=False)
        if loaded.assessment_state is AssessmentDisplayState.PRODUCTION:
            pipeline_assessed += 1
        ranking = loaded.display_ranking
        if ranking and ranking.status is RankingStatus.RANKED:
            if loaded.assessment_state is AssessmentDisplayState.PRODUCTION:
                pipeline_ranked += 1

    summary = DashboardSummaryService(db_session).build_summary(allow_fake=False)
    assert summary.production_assessed_count == pipeline_assessed
    assert summary.production_ranked_count == pipeline_ranked
