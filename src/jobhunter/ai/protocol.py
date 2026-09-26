"""Assessment model port (provider-independent)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from jobhunter.domain.assessment_request import AssessmentRequest


@dataclass(slots=True)
class AssessmentModelResponse:
    provider: str
    model_name: str
    parsed: dict[str, Any] | None = None
    raw_text: str | None = None
    error: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)


class AssessmentModel(Protocol):
    provider: str
    model_name: str

    def assess(self, request: AssessmentRequest) -> AssessmentModelResponse: ...
