"""Deterministic strategy interpretation for tests and dev."""

from __future__ import annotations

import json
from typing import Any

from jobhunter.ai.strategy_protocol import (
    StrategyInterpretationRequest,
    StrategyInterpretationResponse,
)


class FakeStrategyChangeModel:
    provider = "fake"
    model_name = "fake-strategy-v1"

    def __init__(
        self,
        *,
        fixed_payload: dict[str, Any] | None = None,
        raise_provider_error: bool = False,
        malformed: bool = False,
    ) -> None:
        self.fixed_payload = fixed_payload
        self.raise_provider_error = raise_provider_error
        self.malformed = malformed
        self.call_count = 0

    def interpret(
        self, request: StrategyInterpretationRequest
    ) -> StrategyInterpretationResponse:
        self.call_count += 1
        if self.raise_provider_error:
            return StrategyInterpretationResponse(
                provider=self.provider,
                model_name=self.model_name,
                error="simulated provider failure",
            )
        if self.malformed:
            return StrategyInterpretationResponse(
                provider=self.provider,
                model_name=self.model_name,
                raw_text="{not-json",
            )
        payload = (
            self.fixed_payload
            if self.fixed_payload is not None
            else self._auto_payload(request)
        )
        return StrategyInterpretationResponse(
            provider=self.provider,
            model_name=self.model_name,
            parsed=payload,
            raw_text=json.dumps(payload),
        )

    def _auto_payload(self, request: StrategyInterpretationRequest) -> dict[str, Any]:
        text = request.user_message.lower()
        if "clarify" in text or text.strip() == "maybe something":
            return {
                "outcome": "NEEDS_CLARIFICATION",
                "summary": "The request is too vague to apply safely.",
                "assumptions": [],
                "clarification_questions": [
                    "Which themes or criteria should change, and how strongly?"
                ],
                "change_summary": "",
                "mutations": [],
            }
        mutations: list[dict[str, Any]] = []
        if "implementation" in text and "hands-on" in text:
            mutations.append(
                {
                    "op": "SET_CRITERION",
                    "category": "PREFERENCE",
                    "code": "ASSIGNMENT_DELIVERY_MODE",
                    "value": {
                        "implementation": "STRONGLY_PREFERRED",
                        "advisory": "ACCEPTABLE",
                    },
                }
            )
        if "lis" in text or "system integration" in text:
            mutations.append(
                {
                    "op": "SET_THEME_STRENGTH",
                    "theme_key": "lis_implementation",
                    "strength": "STRONGLY_PREFERRED",
                }
            )
            mutations.append(
                {
                    "op": "SET_THEME_STRENGTH",
                    "theme_key": "system_integration",
                    "strength": "STRONGLY_PREFERRED",
                }
            )
        if "junior" in text or "internship" in text:
            mutations.append(
                {
                    "op": "SET_EXCLUSION_ACTIVE",
                    "exclusion_code": "JUNIOR_OR_INTERNSHIP",
                    "is_active": True,
                }
            )
        if "consortium" in text or "multi-person" in text:
            mutations.append(
                {
                    "op": "SET_EXCLUSION_ACTIVE",
                    "exclusion_code": "REQUIRES_MULTI_PERSON_TEAM_OR_CONSORTIUM",
                    "is_active": True,
                }
            )
        if "timor" in text:
            mutations.append(
                {
                    "op": "UPSERT_GEOGRAPHY_PLACE",
                    "place_type": "country",
                    "name": "Timor-Leste",
                    "strength": "STRONGLY_PREFERRED",
                }
            )
        if "remote" in text or "hybrid" in text:
            mutations.append(
                {
                    "op": "SET_CRITERION",
                    "category": "PREFERENCE",
                    "code": "WORK_MODE",
                    "value": {
                        "remote": "PREFERRED",
                        "hybrid": "PREFERRED",
                        "on_site": "ACCEPTABLE",
                    },
                }
            )
        if not mutations:
            return {
                "outcome": "UNUSABLE",
                "summary": "Fake model could not map this message to known mutations.",
                "assumptions": [],
                "clarification_questions": [],
                "change_summary": "",
                "mutations": [],
            }
        return {
            "outcome": "PROPOSED",
            "summary": "Fake model applied keyword-driven mutations.",
            "assumptions": ["Interpretation is deterministic for testing only."],
            "clarification_questions": [],
            "change_summary": request.user_message[:120],
            "mutations": mutations,
        }
