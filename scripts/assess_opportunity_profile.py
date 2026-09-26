"""Run Phase 8 profile/relevance assessment for opportunities."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    import os

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity-id", help="Assess one opportunity by id")
    parser.add_argument(
        "--source-id",
        default="fao-external-jobs",
        help="Assess opportunities linked to this JobSource",
    )
    parser.add_argument(
        "--all-linked",
        action="store_true",
        help="Assess every opportunity with a source link (use with care)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build context and show plan without calling the model or persisting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-assess even when a reusable successful assessment exists",
    )
    parser.add_argument(
        "--include-ineligible",
        action="store_true",
        help="Also assess INELIGIBLE opportunities",
    )
    parser.add_argument(
        "--provider",
        choices=("openai", "fake"),
        default="openai",
        help="Assessment provider (default: openai). Use fake only for explicit dev/test.",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    from sqlalchemy import select

    from jobhunter.ai.factory import resolve_assessment_model
    from jobhunter.application.profile_assessment import OpportunityProfileAssessmentService
    from jobhunter.infrastructure.config import Settings, get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    from jobhunter.infrastructure.persistence.models import OpportunitySourceRow

    settings = get_settings()

    try:
        model = resolve_assessment_model(settings, args.provider)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    settings.require_database_url()
    engine = create_engine_from_settings()
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            service = OpportunityProfileAssessmentService(session, model)
            opportunity_ids: list[str] = []
            if args.opportunity_id:
                opportunity_ids = [args.opportunity_id]
            else:
                stmt = select(OpportunitySourceRow.opportunity_id).distinct()
                if not args.all_linked:
                    stmt = stmt.where(OpportunitySourceRow.source_id == args.source_id)
                opportunity_ids = list(session.scalars(stmt).all())

            if not opportunity_ids:
                print("No opportunities matched.")
                return 0

            for opp_id in opportunity_ids:
                outcome = service.assess_opportunity(
                    opp_id,
                    dry_run=args.dry_run,
                    force=args.force,
                    include_ineligible=args.include_ineligible,
                )
                if outcome.skipped:
                    print(f"{opp_id}: skipped ({outcome.skip_reason})")
                    continue
                assessment = outcome.assessment
                if assessment is None:
                    print(f"{opp_id}: no assessment produced")
                    continue
                reused = "reused" if outcome.reused else "new"
                overall = (
                    (assessment.result or {}).get("overall_relevance")
                    if assessment.result
                    else None
                )
                print(
                    f"{opp_id}: {assessment.status.value} ({reused}) "
                    f"overall={overall} assessment_id={assessment.id}"
                )
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
