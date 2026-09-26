"""Construct AssessmentModel from runtime settings."""

from __future__ import annotations

from enum import StrEnum

from jobhunter.ai.fake_model import FakeAssessmentModel
from jobhunter.ai.openai_model import OpenAIAssessmentModel
from jobhunter.ai.protocol import AssessmentModel
from jobhunter.infrastructure.config import Settings


class AssessmentProvider(StrEnum):
    OPENAI = "openai"
    FAKE = "fake"


_OPENAI_CONFIG_ERROR = (
    "OpenAI assessment is not configured. Set JOBHUNTER_OPENAI_API_KEY and "
    "JOBHUNTER_OPENAI_MODEL, or pass --provider fake for explicit development/test use."
)


def create_assessment_model(settings: Settings) -> AssessmentModel:
    if settings.openai_api_key and settings.openai_model:
        return OpenAIAssessmentModel(
            api_key=settings.openai_api_key,
            model_name=settings.openai_model,
        )
    raise RuntimeError(_OPENAI_CONFIG_ERROR)


def create_fake_assessment_model(**kwargs) -> FakeAssessmentModel:
    return FakeAssessmentModel(**kwargs)


def resolve_assessment_model(
    settings: Settings,
    provider: str | AssessmentProvider,
    **fake_kwargs,
) -> AssessmentModel:
    """Resolve an assessment model for operational use (CLI, scans).

    Tests should construct FakeAssessmentModel directly or pass provider=FAKE.
    """
    kind = (
        provider
        if isinstance(provider, AssessmentProvider)
        else AssessmentProvider(provider.lower().strip())
    )
    if kind is AssessmentProvider.FAKE:
        return create_fake_assessment_model(**fake_kwargs)
    if kind is AssessmentProvider.OPENAI:
        return create_assessment_model(settings)
    raise ValueError(f"Unknown assessment provider: {provider!r}")
