"""Construct AssessmentModel from runtime settings."""

from __future__ import annotations

from jobhunter.ai.fake_model import FakeAssessmentModel
from jobhunter.ai.openai_model import OpenAIAssessmentModel
from jobhunter.ai.protocol import AssessmentModel
from jobhunter.infrastructure.config import Settings


def create_assessment_model(settings: Settings) -> AssessmentModel:
    if settings.openai_api_key and settings.openai_model:
        return OpenAIAssessmentModel(
            api_key=settings.openai_api_key,
            model_name=settings.openai_model,
        )
    raise RuntimeError(
        "OpenAI assessment is not configured. Set JOBHUNTER_OPENAI_API_KEY and "
        "JOBHUNTER_OPENAI_MODEL."
    )


def create_fake_assessment_model(**kwargs) -> FakeAssessmentModel:
    return FakeAssessmentModel(**kwargs)
