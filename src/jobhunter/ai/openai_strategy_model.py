"""OpenAI adapter for conversational search strategy interpretation."""

from __future__ import annotations

import json

from jobhunter.ai.strategy_protocol import (
    StrategyInterpretationRequest,
    StrategyInterpretationResponse,
)

_SYSTEM_PROMPT = """You interpret natural-language requests to adjust a structured JobHunter Search Strategy.
Return ONLY valid JSON with keys:
- outcome: PROPOSED | NEEDS_CLARIFICATION | UNUSABLE
- summary: string
- assumptions: string[]
- clarification_questions: string[]
- change_summary: short string for revision metadata when outcome is PROPOSED
- mutations: array of mutation objects

Allowed mutation ops:
- SET_THEME_STRENGTH {theme_key, strength}
- SET_THEME_ACTIVE {theme_key, is_active}
- SET_CRITERION {category, code, value, strength?, notes?}
- SET_EXCLUSION_ACTIVE {exclusion_code, is_active}
- UPSERT_GEOGRAPHY_PLACE {place_type: region|country, name, strength}

Use only theme_key, StrategyParameterCode, ExclusionCode, and PreferenceStrength values present in current_strategy.
Do not invent new theme keys or parameter codes.
If the user request is ambiguous for a material change, use NEEDS_CLARIFICATION.
Never modify Professional Profile evidence."""


class OpenAIStrategyChangeModel:
    provider = "openai"

    def __init__(self, *, api_key: str, model_name: str) -> None:
        self._api_key = api_key
        self.model_name = model_name

    def interpret(
        self, request: StrategyInterpretationRequest
    ) -> StrategyInterpretationResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            return StrategyInterpretationResponse(
                provider=self.provider,
                model_name=self.model_name,
                error=f"openai package is not installed: {exc}",
            )

        client = OpenAI(api_key=self._api_key)
        payload = json.dumps(
            {
                "user_message": request.user_message,
                "current_strategy": request.current_strategy,
            },
            ensure_ascii=False,
        )
        try:
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": payload},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001
            return StrategyInterpretationResponse(
                provider=self.provider,
                model_name=self.model_name,
                error=str(exc),
            )

        text = completion.choices[0].message.content or ""
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return StrategyInterpretationResponse(
                provider=self.provider,
                model_name=self.model_name,
                raw_text=text,
                error="provider returned non-JSON content",
            )
        if not isinstance(parsed, dict):
            return StrategyInterpretationResponse(
                provider=self.provider,
                model_name=self.model_name,
                raw_text=text,
                error="provider JSON root must be an object",
            )
        return StrategyInterpretationResponse(
            provider=self.provider,
            model_name=self.model_name,
            parsed=parsed,
            raw_text=text,
        )
