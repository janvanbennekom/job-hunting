"""Tabular presentation DTOs for active search strategy (Phase 15)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jobhunter.application.strategy_conversation.dtos import ActiveStrategyView
from jobhunter.application.strategy_display.labels import (
    label_category,
    label_exclusion_code,
    label_parameter_code,
    label_strength,
)


@dataclass(frozen=True, slots=True)
class StrategyThemeRow:
    theme_key: str
    label: str
    strength: str
    active: str
    notes: str


@dataclass(frozen=True, slots=True)
class StrategyCriterionRow:
    category: str
    criterion: str
    strength: str
    active: str
    value_summary: str


@dataclass(frozen=True, slots=True)
class StrategyExclusionRow:
    exclusion: str
    active: str
    condition: str


@dataclass(frozen=True, slots=True)
class StrategyPresentationView:
    revision_number: int | None
    change_summary: str | None
    theme_rows: tuple[StrategyThemeRow, ...]
    preference_rows: tuple[StrategyCriterionRow, ...]
    constraint_rows: tuple[StrategyCriterionRow, ...]
    exclusion_rows: tuple[StrategyExclusionRow, ...]


def build_strategy_presentation(active: ActiveStrategyView) -> StrategyPresentationView:
    theme_rows = tuple(
        StrategyThemeRow(
            theme_key=str(item.get("theme_key", "")),
            label=str(item.get("label", "")),
            strength=label_strength(item.get("strength")),
            active="Yes" if item.get("is_active") else "No",
            notes=str(item.get("notes") or ""),
        )
        for item in active.themes
    )
    preference_rows: list[StrategyCriterionRow] = []
    constraint_rows: list[StrategyCriterionRow] = []
    for item in active.criteria:
        category = str(item.get("category", ""))
        row = StrategyCriterionRow(
            category=label_category(category),
            criterion=label_parameter_code(item.get("code")),
            strength=label_strength(item.get("strength")),
            active="Yes" if item.get("is_active", True) else "No",
            value_summary=_summarize_value(item.get("value")),
        )
        if category == "HARD_CONSTRAINT":
            constraint_rows.append(row)
        else:
            preference_rows.append(row)
    exclusion_rows = tuple(
        StrategyExclusionRow(
            exclusion=label_exclusion_code(item.get("exclusion_code")),
            active="Yes" if item.get("is_active") else "No",
            condition=_summarize_value(item.get("parameters")),
        )
        for item in active.exclusions
    )
    return StrategyPresentationView(
        revision_number=active.revision_number,
        change_summary=active.change_summary,
        theme_rows=theme_rows,
        preference_rows=tuple(preference_rows),
        constraint_rows=tuple(constraint_rows),
        exclusion_rows=exclusion_rows,
    )


def _summarize_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True)
        return text if len(text) <= 120 else text[:117] + "..."
    return str(value)
