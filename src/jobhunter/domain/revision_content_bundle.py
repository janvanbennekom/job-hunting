"""Immutable revision-owned search strategy content (Phase 4A.3)."""

from __future__ import annotations

from dataclasses import dataclass

from jobhunter.domain.exclusion_criterion import ExclusionCriterion
from jobhunter.domain.search_theme import SearchTheme
from jobhunter.domain.strategy_criterion import StrategyCriterion


@dataclass(frozen=True, slots=True)
class RevisionContentBundle:
    """Themes, criteria and exclusions for one strategy revision snapshot."""

    themes: tuple[SearchTheme, ...]
    criteria: tuple[StrategyCriterion, ...]
    exclusions: tuple[ExclusionCriterion, ...]
