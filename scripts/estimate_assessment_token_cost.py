"""Estimate assessment prompt size (read-only, no OpenAI). Compare to 17G-1 baseline."""

from __future__ import annotations

import json
import os
import statistics
import sys
from pathlib import Path


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _summarize(values: list[int]) -> dict[str, int]:
    if not values:
        return {"median": 0, "p90": 0, "max": 0}
    return {
        "median": int(statistics.median(values)),
        "p90": int(statistics.quantiles(values, n=10)[8])
        if len(values) >= 10
        else max(values),
        "max": max(values),
    }


def measure_model_request_from_mapping(model_request: dict) -> dict[str, int]:
    from jobhunter.ai.openai_model import _SYSTEM_PROMPT
    from jobhunter.application.profile_assessment.output_schema import (
        assessment_output_instructions,
        assessment_output_schema,
    )

    user_payload = {
        "assessment_input": model_request,
        "required_output_schema": assessment_output_schema(),
        "output_instructions": assessment_output_instructions(),
    }
    user_content = json.dumps(user_payload, ensure_ascii=False)
    user_msg = (
        "Assess this opportunity against the evidence and strategy. "
        f"Input schema version: {model_request.get('schema_version')}\n"
        + user_content
    )
    total = len(_SYSTEM_PROMPT + user_msg)
    pack = model_request.get("evidence_pack", {})
    opp = json.dumps(model_request.get("opportunity_prompt_text", {}), ensure_ascii=False)
    assign = json.dumps(pack.get("assignments", []), ensure_ascii=False)
    services = json.dumps(pack.get("professional_services", []), ensure_ascii=False)
    profile_other = len(
        json.dumps(
            {
                "positioning_summary": pack.get("positioning_summary"),
                "capabilities": pack.get("capabilities"),
                "skills": pack.get("skills"),
                "languages": pack.get("languages"),
                "countries": pack.get("countries"),
            },
            ensure_ascii=False,
        )
    )
    instructions_schema = len(
        json.dumps(
            {
                "schema": assessment_output_schema(),
                "instructions": assessment_output_instructions(),
                "search_themes": model_request.get("search_themes"),
                "preference_criteria": model_request.get("preference_criteria"),
                "eligibility_rule_summaries": model_request.get(
                    "eligibility_rule_summaries"
                ),
                "instructions_field": model_request.get("instructions"),
            },
            ensure_ascii=False,
        )
    )
    return {
        "total_chars": total,
        "estimated_input_tokens": max(1, total // 4),
        "opportunity_chars": len(opp),
        "assignments_chars": len(assign),
        "services_chars": len(services),
        "profile_other_chars": profile_other,
        "instructions_schema_chars": instructions_schema,
        "assignment_count": len(pack.get("assignments", [])),
        "service_count": len(pack.get("professional_services", [])),
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    _load_env(root / ".env")
    sys.path.insert(0, str(root / "src"))

    from jobhunter.ai.fake_model import FakeAssessmentModel
    from jobhunter.application.profile_assessment.service import (
        OpportunityProfileAssessmentService,
    )
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

    settings = get_settings()
    settings.require_database_url()

    rows: list[dict[str, int]] = []

    with session_scope(create_session_factory(create_engine_from_settings(settings))) as s:
        svc = OpportunityProfileAssessmentService(s, FakeAssessmentModel())
        for opp in OpportunityRepository(s).list_all():
            outcome = svc.assess_opportunity(opp.id, dry_run=True)
            if not outcome.assessment:
                continue
            mr = outcome.assessment.result.get("model_request")
            if not mr:
                continue
            rows.append(measure_model_request_from_mapping(mr))

    def col(key: str) -> list[int]:
        return [row[key] for row in rows]

    report = {
        "profile_assessment_schema": "profile_assessment_v3",
        "population": len(rows),
        "optimized_v3": {
            "total_chars": _summarize(col("total_chars")),
            "estimated_input_tokens": _summarize(col("estimated_input_tokens")),
            "opportunity_chars": _summarize(col("opportunity_chars")),
            "assignments_chars": _summarize(col("assignments_chars")),
            "services_chars": _summarize(col("services_chars")),
            "profile_other_chars": _summarize(col("profile_other_chars")),
            "instructions_schema_chars": _summarize(col("instructions_schema_chars")),
            "assignment_count": _summarize(col("assignment_count")),
            "service_count": _summarize(col("service_count")),
        },
        "legacy_v2_baseline": {
            "total_chars": {"median": 50290, "p90": 63126, "max": None},
            "estimated_input_tokens": {"median": 12572, "p90": 15781, "max": None},
            "note": "Captured in phase-17g-1 investigation before 17G-1A.",
        },
    }
    out = root / "docs" / "analysis" / "phase-17g-1a-token-cost-estimate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
