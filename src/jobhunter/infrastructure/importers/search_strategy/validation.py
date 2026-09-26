"""Validate search strategy seed."""

from __future__ import annotations

from collections import Counter

from jobhunter.domain import (
    RevisionChangeSource,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.domain.strategy_enums import ExclusionCode, PreferenceStrength
from jobhunter.infrastructure.importers.search_strategy.types import SearchStrategySeed


def validate_seed(seed: SearchStrategySeed) -> list[str]:
    errors: list[str] = []
    if seed.schema_version != 1:
        errors.append(f"Unsupported schema_version {seed.schema_version}")
    if not seed.owner_key:
        errors.append("owner_key is required")
    if not seed.change_summary:
        errors.append("change_summary is required")
    try:
        RevisionChangeSource(seed.change_source)
    except ValueError:
        errors.append(f"Invalid change_source {seed.change_source!r}")

    for key, count in Counter(t.key for t in seed.themes).items():
        if not key:
            errors.append("Theme key must be non-empty")
        elif count > 1:
            errors.append(f"Duplicate theme key: {key}")

    for row in seed.themes:
        try:
            PreferenceStrength(row.strength)
        except ValueError:
            errors.append(f"Theme {row.key!r}: invalid strength")

    criterion_keys = [
        (c.category, c.code) for c in seed.criteria
    ]
    for key, count in Counter(criterion_keys).items():
        if count > 1:
            errors.append(f"Duplicate criterion: {key}")

    for row in seed.criteria:
        try:
            StrategyCriterionCategory(row.category)
        except ValueError:
            errors.append(f"Invalid criterion category {row.category!r}")
        try:
            StrategyParameterCode(row.code)
        except ValueError:
            errors.append(f"Invalid criterion code {row.code!r}")
        if row.strength is not None:
            try:
                PreferenceStrength(row.strength)
            except ValueError:
                errors.append(f"Criterion {row.code}: invalid strength")

    for code, count in Counter(e.exclusion_code for e in seed.exclusions).items():
        if count > 1:
            errors.append(f"Duplicate exclusion code: {code}")
    for row in seed.exclusions:
        try:
            ExclusionCode(row.exclusion_code)
        except ValueError:
            errors.append(f"Invalid exclusion_code {row.exclusion_code!r}")

    if not seed.themes:
        errors.append("At least one theme is required")

    return errors
