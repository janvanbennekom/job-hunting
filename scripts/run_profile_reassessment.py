"""Controlled production profile reassessment (dry-run by default)."""

from __future__ import annotations

import argparse
import sys
import time

from _script_bootstrap import bootstrap_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform live OpenAI assessments (default is dry-run only)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of paid assessments in this run",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.0,
        help="Sleep between paid assessment calls",
    )
    parser.add_argument(
        "--include-reusable",
        action="store_true",
        help="Also list opportunities that would reuse (normally only paid targets)",
    )
    args = parser.parse_args(argv)
    bootstrap_repo()

    from jobhunter.ai.factory import resolve_assessment_model
    from jobhunter.application.profile_assessment import OpportunityProfileAssessmentService
    from jobhunter.application.profile_assessment.reassessment_plan import (
        build_reassessment_population,
    )
    from jobhunter.application.ranking import OpportunityRankingService
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    settings = get_settings()
    settings.require_database_url()

    try:
        model = resolve_assessment_model(settings, "openai")
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    assessed = 0
    reused = 0
    failed = 0
    skipped = 0
    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    total_tokens: list[int] = []

    try:
        with session_scope(session_factory) as session:
            population = build_reassessment_population(session, model)
            targets = [
                row
                for row in population.rows
                if not row.would_reuse or args.include_reusable
            ]
            paid_targets = [row for row in population.rows if not row.would_reuse]
            if args.limit is not None:
                paid_targets = paid_targets[: args.limit]

            print(
                f"Population: actionable+eligible={population.actionable_eligible} "
                f"paid_needed={population.needs_paid_assessment} "
                f"would_reuse={population.would_reuse_v3}"
            )
            print(f"Run targets (paid): {len(paid_targets)}")
            for row in paid_targets:
                print(f"  {row.opportunity_id}  {row.title[:90]}")

            if not args.apply:
                print("Dry-run only — no OpenAI calls. Pass --apply to execute.")
                return 0

            service = OpportunityProfileAssessmentService(session, model)
            ranking = OpportunityRankingService(session)
            remaining = len(paid_targets)

            for row in paid_targets:
                remaining -= 1
                try:
                    outcome = service.assess_opportunity(
                        row.opportunity_id,
                        force=False,
                    )
                    if outcome.skipped:
                        skipped += 1
                        print(
                            f"{row.opportunity_id}: skipped ({outcome.skip_reason}) "
                            f"[remaining={remaining}]"
                        )
                        continue
                    if outcome.reused:
                        reused += 1
                        print(
                            f"{row.opportunity_id}: reused "
                            f"[remaining={remaining}]"
                        )
                        continue
                    assessment = outcome.assessment
                    if assessment is None:
                        failed += 1
                        print(
                            f"{row.opportunity_id}: failed (no assessment) "
                            f"[remaining={remaining}]"
                        )
                        continue
                    if not assessment.is_successful:
                        failed += 1
                        print(
                            f"{row.opportunity_id}: {assessment.status.value} "
                            f"[remaining={remaining}]"
                        )
                        continue
                    assessed += 1
                    if assessment.prompt_tokens is not None:
                        prompt_tokens.append(assessment.prompt_tokens)
                    if assessment.completion_tokens is not None:
                        completion_tokens.append(assessment.completion_tokens)
                    if assessment.total_tokens is not None:
                        total_tokens.append(assessment.total_tokens)
                    try:
                        ranking.rank_opportunity(
                            row.opportunity_id,
                            include_fake_assessments=False,
                        )
                    except Exception as rank_exc:  # noqa: BLE001
                        print(
                            f"{row.opportunity_id}: ranked warning: {rank_exc}",
                            file=sys.stderr,
                        )
                    print(
                        f"{row.opportunity_id}: assessed "
                        f"overall={(assessment.result or {}).get('overall_relevance')} "
                        f"tokens={assessment.total_tokens} "
                        f"[remaining={remaining}]"
                    )
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    print(
                        f"{row.opportunity_id}: error {exc} [remaining={remaining}]",
                        file=sys.stderr,
                    )
                if args.delay_seconds > 0 and remaining > 0:
                    time.sleep(args.delay_seconds)

            print()
            print(
                f"Summary: assessed={assessed} reused={reused} "
                f"failed={failed} skipped={skipped}"
            )
            if prompt_tokens:
                print(
                    f"Token totals this run: prompt={sum(prompt_tokens)} "
                    f"completion={sum(completion_tokens)} "
                    f"total={sum(total_tokens)}"
                )
            return 0 if failed == 0 else 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
