"""OpenAI Chat Completions adapter for profile assessment."""

from __future__ import annotations

import json
from typing import Any

from jobhunter.ai.protocol import AssessmentModelResponse
from jobhunter.domain.assessment_request import AssessmentRequest

_SYSTEM_PROMPT = """You are an expert assessor for international Geo-ICT and land administration consulting opportunities.
Return ONLY valid JSON matching the requested schema.
Use UNKNOWN or INSUFFICIENT_EVIDENCE when evidence is missing.
Never invent ToR requirements, qualifications, durations, team structures, or profile evidence.
Only reference profile entity IDs present in evidence_pack.
Opportunity excerpts must be exact substrings of the supplied opportunity fields.
Distinguish OPPORTUNITY_FACT, PROFILE_FACT, and INFERENCE using the basis field.
When source_data_sufficiency is LIST_SUMMARY_ONLY, avoid inferring missing vacancy requirements."""


class OpenAIAssessmentModel:
    provider = "openai"

    def __init__(self, *, api_key: str, model_name: str) -> None:
        self._api_key = api_key
        self.model_name = model_name

    def assess(self, request: AssessmentRequest) -> AssessmentModelResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            return AssessmentModelResponse(
                provider=self.provider,
                model_name=self.model_name,
                error=f"openai package is not installed: {exc}",
            )

        client = OpenAI(api_key=self._api_key)
        user_content = json.dumps(request.to_mapping(), ensure_ascii=False)
        try:
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Assess this opportunity against the evidence and strategy. "
                            f"Schema version: {request.schema_version}\n"
                            f"{user_content}"
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001 — surface provider failure
            return AssessmentModelResponse(
                provider=self.provider,
                model_name=self.model_name,
                error=str(exc),
            )

        text = completion.choices[0].message.content or ""
        usage: dict[str, Any] = {}
        if completion.usage is not None:
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens,
            }
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return AssessmentModelResponse(
                provider=self.provider,
                model_name=self.model_name,
                raw_text=text,
                error="provider returned non-JSON content",
                usage=usage,
            )
        if not isinstance(parsed, dict):
            return AssessmentModelResponse(
                provider=self.provider,
                model_name=self.model_name,
                raw_text=text,
                error="provider JSON root must be an object",
                usage=usage,
            )
        return AssessmentModelResponse(
            provider=self.provider,
            model_name=self.model_name,
            parsed=parsed,
            raw_text=text,
            usage=usage,
        )
