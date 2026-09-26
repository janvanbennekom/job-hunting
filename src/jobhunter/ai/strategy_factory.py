"""Construct StrategyChangeModel from runtime settings."""

from __future__ import annotations

from enum import StrEnum

from jobhunter.ai.fake_strategy_model import FakeStrategyChangeModel
from jobhunter.ai.openai_strategy_model import OpenAIStrategyChangeModel
from jobhunter.ai.strategy_protocol import StrategyChangeModel
from jobhunter.infrastructure.config import Settings

_OPENAI_CONFIG_ERROR = (
    "OpenAI strategy interpretation is not configured. Set JOBHUNTER_OPENAI_API_KEY "
    "and JOBHUNTER_OPENAI_MODEL, or pass provider=fake for explicit development/test use."
)


class StrategyProvider(StrEnum):
    OPENAI = "openai"
    FAKE = "fake"


def create_strategy_change_model(settings: Settings) -> StrategyChangeModel:
    if settings.openai_api_key and settings.openai_model:
        return OpenAIStrategyChangeModel(
            api_key=settings.openai_api_key,
            model_name=settings.openai_model,
        )
    raise RuntimeError(_OPENAI_CONFIG_ERROR)


def create_fake_strategy_change_model(**kwargs) -> FakeStrategyChangeModel:
    return FakeStrategyChangeModel(**kwargs)


def resolve_strategy_change_model(
    settings: Settings,
    provider: str | StrategyProvider,
    **fake_kwargs,
) -> StrategyChangeModel:
    kind = (
        provider
        if isinstance(provider, StrategyProvider)
        else StrategyProvider(provider.lower().strip())
    )
    if kind is StrategyProvider.FAKE:
        return create_fake_strategy_change_model(**fake_kwargs)
    if kind is StrategyProvider.OPENAI:
        return create_strategy_change_model(settings)
    raise ValueError(f"Unknown strategy provider: {provider!r}")
