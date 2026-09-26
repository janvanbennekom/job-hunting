"""Parsed search strategy seed structures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ThemeSeedRow:
    key: str
    label: str
    strength: str
    is_active: bool
    notes: str | None
    sort_order: int


@dataclass(slots=True)
class CriterionSeedRow:
    category: str
    code: str
    value: dict[str, Any]
    strength: str | None
    is_active: bool
    notes: str | None
    sort_order: int


@dataclass(slots=True)
class ExclusionSeedRow:
    exclusion_code: str
    parameters: dict[str, Any] | None
    is_active: bool
    notes: str | None


@dataclass(slots=True)
class SearchStrategySeed:
    schema_version: int
    owner_key: str
    change_summary: str
    change_source: str
    themes: list[ThemeSeedRow]
    criteria: list[CriterionSeedRow]
    exclusions: list[ExclusionSeedRow]
