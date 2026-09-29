"""Read-only token summary for a small set of pilot assessments."""

from __future__ import annotations

import argparse
import json
import statistics
import sys

from _script_bootstrap import bootstrap_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--opportunity-id",
        action="append",
        dest="opportunity_ids",
        required=True,
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    bootstrap_repo()

    from jobhunter.application.review.opportunity_reads import OpportunityPipelineReader
    from jobhunter.infrastructure.importers.professional_services.identity import (
        PRIMARY_PROFILE_KEY,
    )
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
    from jobhunter.infrastructure.persistence.strategy_repositories import (
        SearchStrategyRepository,
    )

    settings = get_settings()
    settings.require_database_url()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            strategy = SearchStrategyRepository(session).get_by_owner_key(
                PRIMARY_PROFILE_KEY
            )
            if strategy is None or strategy.current_revision_id is None:
                print("No active search strategy revision.", file=sys.stderr)
                return 1
            revision_id = strategy.current_revision_id
            pipeline = OpportunityPipelineReader(session)
            opp_repo = OpportunityRepository(session)

            rows: list[dict] = []
            for opp_id in args.opportunity_ids:
                opp = opp_repo.get_by_id(opp_id)
                if opp is None:
                    print(f"Unknown opportunity: {opp_id}", file=sys.stderr)
                    return 1
                assessment = pipeline.load(
                    opp, revision_id, allow_fake=False
                ).display_assessment
                rows.append(
                    {
                        "opportunity_id": opp_id,
                        "title": opp.title[:80],
                        "prompt_tokens": assessment.prompt_tokens
                        if assessment
                        else None,
                        "completion_tokens": assessment.completion_tokens
                        if assessment
                        else None,
                        "total_tokens": assessment.total_tokens
                        if assessment
                        else None,
                    }
                )

            prompts = [r["prompt_tokens"] for r in rows if r["prompt_tokens"]]
            completions = [
                r["completion_tokens"] for r in rows if r["completion_tokens"]
            ]
            totals = [r["total_tokens"] for r in rows if r["total_tokens"]]

            def _mean(vals: list[int]) -> float | None:
                return statistics.mean(vals) if vals else None

            def _median(vals: list[int]) -> float | None:
                return statistics.median(vals) if vals else None

            summary = {
                "assessments": rows,
                "prompt_tokens": {
                    "per_assessment": prompts,
                    "mean": _mean(prompts),
                    "median": _median(prompts),
                },
                "completion_tokens": {
                    "per_assessment": completions,
                    "mean": _mean(completions),
                    "median": _median(completions),
                },
                "total_tokens": {
                    "per_assessment": totals,
                    "mean": _mean(totals),
                    "median": _median(totals),
                    "sum": sum(totals) if totals else None,
                },
                "offline_estimate_reference_median_input_tokens": 7633,
            }

            if args.json:
                print(json.dumps(summary, indent=2))
                return 0

            for row in rows:
                print(
                    f"{row['opportunity_id']}: prompt={row['prompt_tokens']} "
                    f"completion={row['completion_tokens']} total={row['total_tokens']}"
                )
            print()
            print(f"mean prompt_tokens: {summary['prompt_tokens']['mean']}")
            print(f"median prompt_tokens: {summary['prompt_tokens']['median']}")
            print(f"sum total_tokens: {summary['total_tokens']['sum']}")
            print(
                "reference offline median estimated input tokens (17G-1A): 7633"
            )
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
