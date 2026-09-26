"""Strategy change interpretation port (Phase 11)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class StrategyInterpretationRequest:
    user_message: str
    current_strategy: dict[str, Any]
    owner_key: str


@dataclass(slots=True)
class StrategyInterpretationResponse:
    provider: str
    model_name: str
    parsed: dict[str, Any] | None = None
    raw_text: str | None = None
    error: str | None = None


class StrategyChangeModel(Protocol):
    provider: str
    model_name: str

    def interpret(
        self, request: StrategyInterpretationRequest
    ) -> StrategyInterpretationResponse: ...
