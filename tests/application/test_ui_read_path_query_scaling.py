"""17H-1: SQL count must not scale linearly with opportunity count."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.application.ranking import OpportunityRankingService
from jobhunter.application.review.dashboard_summary import DashboardSummaryService
from jobhunter.application.review.dtos import OpportunityQueueFilters
from jobhunter.application.review.opportunity_detail import OpportunityDetailService
from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService
from jobhunter.domain.assessment_enums import AssessmentStatus, OverallRelevance
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.relevance_queue_enums import RelevanceQueueView
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

pytestmark = pytest.mark.integration

# Bulk load should use a small constant number of queries regardless of N.
_MAX_SQL_GROWTH_RATIO = 2.5
_BASELINE_SQL_CEILING = 40


def _count_sql(engine: Engine, fn) -> int:
    count = 0

    def before(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        nonlocal count
        count += 1

    event.listen(engine, "before_cursor_execute", before)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", before)
    return count


def _add_bench_opp(session: Session, suffix: str) -> str:
    oid = f"bench-scale-{suffix}-{uuid.uuid4().hex[:8]}"
    OpportunityRepository(session).save(
        Opportunity(
            id=oid,
            title=f"Scale test {suffix}",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    decision = EligibilityFilterService(session).evaluate_and_persist(oid).decision
    OpportunityProfileAssessmentRepository(session).save(
        OpportunityProfileAssessment(
            opportunity_id=oid,
            search_strategy_revision_id=decision.search_strategy_revision_id,
            eligibility_decision_id=decision.id,
            assessed_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            status=AssessmentStatus.SUCCEEDED,
            input_digest="a" * 64,
            opportunity_content_digest="b" * 64,
            profile_evidence_digest="c" * 64,
            prompt_schema_version="profile_assessment_v4",
            model_provider="openai",
            model_name="test",
            result={"overall_relevance": OverallRelevance.MODERATE_FIT.value},
        )
    )
    OpportunityRankingService(session).rank_opportunity(oid)
    return oid


def _seed_many(session: Session, count: int) -> list[str]:
    return [_add_bench_opp(session, str(i)) for i in range(count)]


def test_list_queue_sql_bounded_vs_population(db_session: Session) -> None:
    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    assert isinstance(engine, Engine)

    baseline = _count_sql(
        engine, lambda: OpportunityReviewQueryService(db_session).list_queue()
    )
    assert baseline <= _BASELINE_SQL_CEILING, f"baseline sql={baseline}"

    _seed_many(db_session, 8)
    db_session.commit()
    with_more = _count_sql(
        engine, lambda: OpportunityReviewQueryService(db_session).list_queue()
    )

    ratio = with_more / baseline if baseline else with_more
    assert ratio <= _MAX_SQL_GROWTH_RATIO, (
        f"SQL grew too much: baseline={baseline} with_more={with_more} ratio={ratio}"
    )


def test_opportunities_page_path_single_snapshot_sql(db_session: Session) -> None:
    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    base = OpportunityQueueFilters(
        relevance_queue=RelevanceQueueView.PRIMARY,
        hide_dismissed=True,
    )
    base_only = OpportunityQueueFilters(
        include_ineligible=False,
        include_non_actionable_lifecycle=False,
    )

    def run() -> None:
        svc = OpportunityReviewQueryService(db_session)
        svc.list_queue_with_snapshot(base_only, base)

    sql = _count_sql(engine, run)
    assert sql <= _BASELINE_SQL_CEILING


def test_home_build_summary_sql_bounded(db_session: Session) -> None:
    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    sql = _count_sql(
        engine,
        lambda: DashboardSummaryService(db_session).build_summary(allow_fake=False),
    )
    assert sql <= _BASELINE_SQL_CEILING + 5


def test_detail_sql_bounded(db_session: Session) -> None:
    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    opp = OpportunityRepository(db_session).list_all()[0]

    def run() -> None:
        OpportunityDetailService(db_session).get_detail(opp.id, allow_fake=False)

    sql = _count_sql(engine, run)
    assert sql <= _BASELINE_SQL_CEILING + 15
