"""Production-only profile assessment batch step for automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from jobhunter.ai.protocol import AssessmentModel
from jobhunter.application.profile_assessment import OpportunityProfileAssessmentService
from jobhunter.ai.factory import create_assessment_model
from jobhunter.infrastructure.config import Settings, get_settings


@dataclass(slots=True)
class AssessmentBatchResult:
    skipped: bool = False
    skip_reason: str | None = None
    assessed: int = 0
    reused: int = 0
    skipped_opportunities: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


AssessmentModelFactory = Callable[[Settings], AssessmentModel]


def run_production_assessment_batch(
    session: Session,
    opportunity_ids: list[str],
    *,
    settings: Settings | None = None,
    required: bool = False,
    model_factory: AssessmentModelFactory | None = None,
) -> AssessmentBatchResult:
    """Assess opportunities using production OpenAI configuration only.

    Never uses FakeAssessmentModel. When OpenAI is not configured, skips unless
    `required` is True (then raises RuntimeError).
    """
    resolved_settings = settings or get_settings()
    factory = model_factory or create_assessment_model
    try:
        model = factory(resolved_settings)
    except RuntimeError as exc:
        if required:
            raise RuntimeError(
                "Production assessment is required but OpenAI is not configured"
            ) from exc
        return AssessmentBatchResult(
            skipped=True,
            skip_reason="openai_not_configured",
        )

    if model.provider == "fake":
        raise RuntimeError(
            "FakeAssessmentModel is not permitted in production automation"
        )

    service = OpportunityProfileAssessmentService(session, model)
    result = AssessmentBatchResult()
    seen: set[str] = set()
    for opportunity_id in opportunity_ids:
        if opportunity_id in seen:
            continue
        seen.add(opportunity_id)
        try:
            outcome = service.assess_opportunity(opportunity_id)
            if outcome.skipped:
                result.skipped_opportunities += 1
            elif outcome.reused:
                result.reused += 1
            elif outcome.assessment is not None:
                result.assessed += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.errors.append(f"{opportunity_id}: {exc}")
    return result
