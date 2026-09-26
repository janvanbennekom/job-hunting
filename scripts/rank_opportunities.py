"""Run Phase 9 deterministic opportunity ranking."""

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
    parser.add_argument("--opportunity-id", help="Rank one opportunity by id")
    parser.add_argument(
        "--source-id",
        default="fao-external-jobs",
        help="Rank opportunities linked to this JobSource",
    )
    parser.add_argument(
        "--all-linked",
        action="store_true",
        help="Rank every opportunity with a source link (use with care)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute without persisting")
    parser.add_argument("--force", action="store_true", help="Ignore digest reuse")
    parser.add_argument(
        "--include-fake-assessments",
        action="store_true",
        help="DEV ONLY: allow model_provider=fake assessments (not production ranking)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    from sqlalchemy import select

    from jobhunter.application.ranking import OpportunityRankingService
    from jobhunter.domain.ranking_enums import RankingStatus
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.assessment_repositories import (
        OpportunityProfileAssessmentRepository,
    )
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    from jobhunter.infrastructure.persistence.models import OpportunitySourceRow
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

    settings = get_settings()
    settings.require_database_url()

    if args.include_fake_assessments:
        print(
            "WARNING: development mode — rankings may use NON_PRODUCTION fake assessments."
        )

    engine = create_engine_from_settings()
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            service = OpportunityRankingService(session)
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

            outcomes = service.rank_opportunity_ids(
                opportunity_ids,
                include_fake_assessments=args.include_fake_assessments,
                force=args.force,
                dry_run=args.dry_run,
            )

            ranked_views = service.current_ranked_views(
                opportunity_ids,
                include_fake_assessments=args.include_fake_assessments,
                force_recompute=False,
            )
            assessments = OpportunityProfileAssessmentRepository(session)
            opportunities = OpportunityRepository(session)

            position = 0
            for view in ranked_views:
                position += 1
                opp = view.opportunity
                ranking = view.ranking
                assessment_id = ranking.profile_assessment_id
                provider = model = overall = sufficiency = "—"
                if assessment_id:
                    assessment = assessments.get_by_id(assessment_id)
                    if assessment and assessment.result:
                        provider = assessment.model_provider
                        model = assessment.model_name
                        overall = assessment.result.get("overall_relevance", "—")
                        sufficiency = assessment.result.get(
                            "source_data_sufficiency", "—"
                        )
                elig = "—"
                if ranking.eligibility_decision_id:
                    from jobhunter.infrastructure.persistence.eligibility_repositories import (
                        EligibilityDecisionRepository,
                    )

                    decision = EligibilityDecisionRepository(session).get_by_id(
                        ranking.eligibility_decision_id
                    )
                    if decision:
                        elig = decision.status.value
                warnings = ",".join(ranking.warnings) if ranking.warnings else ""
                factor_codes = ",".join(f.code for f in ranking.factors[:4])
                print(
                    f"{position:>3} | {ranking.priority_band} | {ranking.status.value} | "
                    f"{opp.title[:50]} | rel={overall} | elig={elig} | "
                    f"deadline={opp.deadline} | suff={sufficiency} | "
                    f"provider={provider}/{model} | warn={warnings} | factors={factor_codes}"
                )

            for outcome in outcomes:
                if outcome.ranking.status is not RankingStatus.RANKED:
                    opp = opportunities.get_by_id(outcome.ranking.opportunity_id)
                    title = opp.title if opp else outcome.ranking.opportunity_id
                    print(
                        f"— | {outcome.ranking.status.value} | {title[:50]} | "
                        f"reason={outcome.ranking.unranked_reason or outcome.ranking.exclusion_reason} "
                        f"({'reused' if outcome.reused else 'new'})"
                    )
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
