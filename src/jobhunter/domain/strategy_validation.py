"""Search strategy domain validation helpers."""

from __future__ import annotations

import re
from typing import Any

from jobhunter.domain.identifiers import require_non_empty
from jobhunter.domain.strategy_enums import (
    PreferenceStrength,
    StrategyCriterionCategory,
    StrategyParameterCode,
)

_CONTENT_HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def require_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def require_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def require_content_hash(value: str) -> str:
    normalized = require_non_empty(value, "content_hash").lower()
    if not _CONTENT_HASH_PATTERN.match(normalized):
        raise ValueError(
            "content_hash must be a 64-character lowercase hexadecimal SHA-256 digest"
        )
    return normalized


def require_strength(raw: Any, field_name: str) -> PreferenceStrength:
    if isinstance(raw, PreferenceStrength):
        return raw
    if not isinstance(raw, str):
        raise ValueError(f"{field_name} must be a PreferenceStrength value")
    return PreferenceStrength(raw.strip())


def require_non_empty_string_list(
    raw: Any,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if raw is None:
        if allow_empty:
            return ()
        raise ValueError(f"{field_name} is required")
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{field_name} must be a list of strings")
    items: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} entries must be strings")
        stripped = item.strip()
        if not stripped:
            raise ValueError(f"{field_name} entries must be non-empty")
        items.append(stripped)
    if not items and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    return tuple(items)


def reject_unknown_keys(raw: dict[str, Any], allowed: frozenset[str], context: str) -> None:
    unknown = set(raw) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"{context} contains unknown keys: {names}")


def validate_criterion_strength_semantics(
    category: StrategyCriterionCategory,
    code: StrategyParameterCode,
    strength: PreferenceStrength | None,
) -> None:
    """Enforce where PreferenceStrength is stored on StrategyCriterion.

    - HARD_CONSTRAINT: criterion strength must always be omitted.
    - PREFERENCE with one logical preference (e.g. travel pattern, duration
      band): use StrategyCriterion.strength.
    - PREFERENCE with several independently scored alternatives: embed
      PreferenceStrength in the typed value (delivery mode, work mode,
      engagement model, geography places).
    """
    if category is StrategyCriterionCategory.HARD_CONSTRAINT:
        if strength is not None:
            raise ValueError("HARD_CONSTRAINT must not set preference strength")
        return

    if category is not StrategyCriterionCategory.PREFERENCE:
        return

    codes_with_embedded_strengths = {
        StrategyParameterCode.ASSIGNMENT_DELIVERY_MODE,
        StrategyParameterCode.WORK_MODE,
        StrategyParameterCode.ENGAGEMENT_MODEL,
        StrategyParameterCode.GEOGRAPHY,
    }
    codes_requiring_criterion_strength = {
        StrategyParameterCode.TRAVEL_PATTERN,
        StrategyParameterCode.ASSIGNMENT_DURATION,
    }

    if code in codes_with_embedded_strengths and strength is not None:
        raise ValueError(
            f"{code.value} stores preference strength in structured value, "
            "not on the criterion"
        )
    if code in codes_requiring_criterion_strength and strength is None:
        raise ValueError(f"{code.value} requires criterion-level preference strength")


def validate_exclusion_parameters(
    exclusion_code: Any,
    parameters: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if parameters is None:
        return None
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a mapping or None")
    if parameters:
        raise ValueError(
            f"Exclusion {exclusion_code!s} does not accept parameters in the MVP"
        )
    return None
