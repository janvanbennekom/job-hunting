"""Phase 17H-0: read-only query-count and timing benchmarks for operator UI paths.

Does not write to the database except optional --synthetic-seed (local/test only).

Usage:
  python scripts/benchmark_ui_read_paths.py
  python scripts/benchmark_ui_read_paths.py --synthetic-seed 100
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from _script_bootstrap import bootstrap_repo  # noqa: E402


@dataclass
class BenchResult:
    label: str
    sql_statements: int
    seconds: float
    opportunity_count: int
    rows_returned: int | None = None


@contextmanager
def count_sql(engine: Engine):
    count = 0

    def before(
        conn, cursor, statement, parameters, context, executemany
    ):  # noqa: ANN001
        nonlocal count
        count += 1

    event.listen(engine, "before_cursor_execute", before)
    try:
        yield lambda: count
    finally:
        event.remove(engine, "before_cursor_execute", before)


def _opportunity_count(session: Session) -> int:
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

    return len(OpportunityRepository(session).list_all())


def bench_home(session: Session, engine: Engine) -> BenchResult:
    from jobhunter.application.review.dashboard_summary import DashboardSummaryService

    n = _opportunity_count(session)
    with count_sql(engine) as get_count:
        t0 = time.perf_counter()
        DashboardSummaryService(session).build_summary(allow_fake=False)
        elapsed = time.perf_counter() - t0
    return BenchResult("home_build_summary", get_count(), elapsed, n)


def bench_opportunities_page(session: Session, engine: Engine) -> BenchResult:
    """Mirrors opportunities.py: segment counts + filtered list_queue + dataframe."""
    from jobhunter.application.review.dtos import OpportunityQueueFilters
    from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService
    from jobhunter.domain.relevance_queue_enums import RelevanceQueueView
    from jobhunter.ui.streamlit.opportunities_table import build_opportunity_queue_dataframe

    n = _opportunity_count(session)
    base = OpportunityQueueFilters(
        allow_fake=False,
        include_ineligible=False,
        include_non_actionable_lifecycle=False,
        relevance_queue=RelevanceQueueView.PRIMARY,
        hide_dismissed=True,
    )
    query = OpportunityReviewQueryService(session)

    base_only = OpportunityQueueFilters(
        allow_fake=base.allow_fake,
        include_ineligible=base.include_ineligible,
        include_non_actionable_lifecycle=base.include_non_actionable_lifecycle,
    )
    with count_sql(engine) as get_count:
        t0 = time.perf_counter()
        query.count_relevance_segments(base_only)
        items = query.list_queue(base)
        build_opportunity_queue_dataframe(items)
        elapsed = time.perf_counter() - t0
    return BenchResult(
        "opportunities_page_backend",
        get_count(),
        elapsed,
        n,
        rows_returned=len(items),
    )


def bench_list_queue_once(session: Session, engine: Engine) -> BenchResult:
    from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService

    n = _opportunity_count(session)
    with count_sql(engine) as get_count:
        t0 = time.perf_counter()
        items = OpportunityReviewQueryService(session).list_queue()
        elapsed = time.perf_counter() - t0
    return BenchResult("list_queue_single", get_count(), elapsed, n, len(items))


def bench_detail(session: Session, engine: Engine, opportunity_id: str | None) -> BenchResult:
    from jobhunter.application.review.opportunity_detail import OpportunityDetailService
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

    opps = OpportunityRepository(session).list_all()
    n = len(opps)
    oid = opportunity_id or (opps[0].id if opps else None)
    if not oid:
        return BenchResult("detail_get_detail", 0, 0.0, 0)

    with count_sql(engine) as get_count:
        t0 = time.perf_counter()
        OpportunityDetailService(session).get_detail(oid, allow_fake=False)
        elapsed = time.perf_counter() - t0
    return BenchResult("detail_get_detail", get_count(), elapsed, n)


def seed_synthetic_opportunities(session: Session, count: int) -> list[str]:
    """Insert minimal eligible opps for scaling benchmarks (local/test)."""
    from jobhunter.application.eligibility import EligibilityFilterService
    from jobhunter.application.ranking import OpportunityRankingService
    from jobhunter.domain.assessment_enums import AssessmentStatus, OverallRelevance
    from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
    from jobhunter.domain.opportunity import Opportunity
    from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
    from jobhunter.infrastructure.persistence.assessment_repositories import (
        OpportunityProfileAssessmentRepository,
    )
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

    created: list[str] = []
    opportunities = OpportunityRepository(session)
    for i in range(count):
        oid = f"bench-ui-{uuid.uuid4().hex[:12]}"
        opportunities.save(
            Opportunity(
                id=oid,
                title=f"Benchmark synthetic {i}",
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
                assessed_at=datetime.now(timezone.utc),
                status=AssessmentStatus.SUCCEEDED,
                input_digest="d" * 64,
                opportunity_content_digest="e" * 64,
                profile_evidence_digest="f" * 64,
                prompt_schema_version="profile_assessment_v4",
                model_provider="openai",
                model_name="bench",
                result={"overall_relevance": OverallRelevance.WEAK_FIT.value},
            )
        )
        OpportunityRankingService(session).rank_opportunity(oid)
        created.append(oid)
    session.flush()
    return created


def main() -> int:
    bootstrap_repo()
    parser = argparse.ArgumentParser(description="17H-0 UI read-path benchmarks")
    parser.add_argument(
        "--synthetic-seed",
        type=int,
        default=0,
        help="Create N synthetic opportunities before benchmark (local DB only)",
    )
    parser.add_argument(
        "--detail-id",
        default=None,
        help="Opportunity id for detail benchmark",
    )
    args = parser.parse_args()

    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
    )

    settings = get_settings()
    settings.require_database_url()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            if args.synthetic_seed > 0:
                if settings.is_production():
                    print("Refusing --synthetic-seed when JOBHUNTER_ENV=production", file=sys.stderr)
                    return 2
                print(f"Seeding {args.synthetic_seed} synthetic opportunities (rollback after)…")
                seed_synthetic_opportunities(session, args.synthetic_seed)

            results = [
                bench_home(session, engine),
                bench_list_queue_once(session, engine),
                bench_opportunities_page(session, engine),
                bench_detail(session, engine, args.detail_id),
            ]
            if args.synthetic_seed > 0:
                session.rollback()
                print(f"Rolled back {args.synthetic_seed} synthetic rows (no persistent writes).")
    finally:
        engine.dispose()

    print("Phase 17H-0 UI read-path benchmark (read-only except optional seed)")
    print("-" * 72)
    for r in results:
        per_opp = r.sql_statements / r.opportunity_count if r.opportunity_count else 0
        extra = f" rows={r.rows_returned}" if r.rows_returned is not None else ""
        print(
            f"{r.label:28}  opps={r.opportunity_count:4}  "
            f"sql={r.sql_statements:5}  ({per_opp:.1f}/opp)  "
            f"time={r.seconds:.3f}s{extra}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
