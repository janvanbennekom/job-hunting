"""Offline size metrics for assessment model requests."""

from __future__ import annotations

import json
from dataclasses import dataclass

from jobhunter.ai.openai_model import _SYSTEM_PROMPT
from jobhunter.application.profile_assessment.output_schema import (
    assessment_output_instructions,
    assessment_output_schema,
)
from jobhunter.domain.assessment_request import AssessmentRequest


def _chars_to_tokens(char_count: int) -> int:
    return max(1, char_count // 4)


@dataclass(slots=True)
class ModelRequestMetrics:
    total_chars: int
    estimated_input_tokens: int
    opportunity_chars: int
    assignments_chars: int
    services_chars: int
    profile_other_chars: int
    instructions_schema_chars: int
    assignment_count: int
    service_count: int


def measure_openai_user_message(request: AssessmentRequest) -> tuple[str, ModelRequestMetrics]:
    user_payload = {
        "assessment_input": request.to_model_mapping(),
        "required_output_schema": assessment_output_schema(),
        "output_instructions": assessment_output_instructions(),
    }
    user_content = json.dumps(user_payload, ensure_ascii=False)
    user_msg = (
        "Assess this opportunity against the evidence and strategy. "
        f"Input schema version: {request.schema_version}\n"
        + user_content
    )
    full = _SYSTEM_PROMPT + user_msg
    model_input = request.to_model_mapping()
    pack = model_input["evidence_pack"]
    opp_chars = len(json.dumps(model_input["opportunity_prompt_text"], ensure_ascii=False))
    assign_chars = len(json.dumps(pack.get("assignments", []), ensure_ascii=False))
    svc_chars = len(json.dumps(pack.get("professional_services", []), ensure_ascii=False))
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
    instr_schema = len(
        json.dumps(
            {
                "schema": assessment_output_schema(),
                "instructions": assessment_output_instructions(),
                "search_themes": model_input.get("search_themes"),
                "preference_criteria": model_input.get("preference_criteria"),
                "eligibility_rule_summaries": model_input.get(
                    "eligibility_rule_summaries"
                ),
                "instructions_field": model_input.get("instructions"),
            },
            ensure_ascii=False,
        )
    )
    metrics = ModelRequestMetrics(
        total_chars=len(full),
        estimated_input_tokens=_chars_to_tokens(len(full)),
        opportunity_chars=opp_chars,
        assignments_chars=assign_chars,
        services_chars=svc_chars,
        profile_other_chars=profile_other,
        instructions_schema_chars=instr_schema,
        assignment_count=len(pack.get("assignments", [])),
        service_count=len(pack.get("professional_services", [])),
    )
    return full, metrics


def measure_model_request(request: AssessmentRequest) -> ModelRequestMetrics:
    _, metrics = measure_openai_user_message(request)
    return metrics
