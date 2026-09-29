"""Read-only reassessment population summary (Part D/E)."""

from __future__ import annotations

import argparse
import json
import sys

from _script_bootstrap import bootstrap_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    bootstrap_repo()

    from jobhunter.ai.factory import resolve_assessment_model
    from jobhunter.application.profile_assessment.reassessment_plan import (
        build_reassessment_population,
    )
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    settings = get_settings()
    settings.require_database_url()
    model = resolve_assessment_model(settings, "openai")
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    pilot = {
        "mean_prompt": 9341,
        "median_prompt": 9022,
        "mean_completion": int((1843 + 1746 + 1560 + 1536 + 1678) / 5),
        "median_completion": 1678,
        "mean_total": int(55068 / 5),
        "min_prompt": 8544,
        "max_prompt": 10187,
        "min_total": 10104,
        "max_total": 11723,
    }

    try:
        with session_scope(session_factory) as session:
            pop = build_reassessment_population(session, model)
            n = pop.needs_paid_assessment
            forecast = {
                "paid_calls": n,
                "prompt_tokens_base": n * pilot["median_prompt"],
                "completion_tokens_base": n * pilot["median_completion"],
                "total_tokens_base": n * pilot["mean_total"],
                "prompt_tokens_low": n * pilot["min_prompt"],
                "prompt_tokens_high": n * pilot["max_prompt"],
                "total_tokens_low": n * pilot["min_total"],
                "total_tokens_high": n * pilot["max_total"],
            }
            payload = {
                "population": {
                    "total_opportunities": pop.total_opportunities,
                    "actionable_eligible": pop.actionable_eligible,
                    "by_lifecycle": pop.by_lifecycle,
                    "by_eligibility": pop.by_eligibility,
                    "latest_success_schema": pop.latest_success_schema,
                    "needs_paid_assessment": pop.needs_paid_assessment,
                    "would_reuse_current_digest": pop.would_reuse_v3,
                    "excluded_non_actionable_lifecycle": pop.excluded_non_actionable_lifecycle,
                    "excluded_ineligible": pop.excluded_ineligible,
                },
                "inclusion_rule": (
                    "ELIGIBLE + actionable lifecycle (NEW, UPDATED, STILL_OPEN); "
                    "exclude when a successful non-fake assessment already exists "
                    "for the current input_digest (schema, model, evidence, opportunity, "
                    "strategy revision)."
                ),
                "token_forecast_from_pilot": forecast,
                "pilot_reference": pilot,
            }
            if args.json:
                print(json.dumps(payload, indent=2))
                return 0
            print(json.dumps(payload, indent=2))
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
