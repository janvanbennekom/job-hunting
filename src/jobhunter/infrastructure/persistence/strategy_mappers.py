"""Domain ↔ persistence mapping for search strategy."""

from __future__ import annotations

from typing import Any

from jobhunter.domain import (
    ExclusionCriterion,
    SearchStrategy,
    SearchStrategyRevision,
    SearchTheme,
    StrategyCriterion,
)
from jobhunter.domain.strategy_criterion_values import (
    criterion_value_to_mapping,
    parse_criterion_value,
)
from jobhunter.domain.strategy_enums import (
    ExclusionCode,
    PreferenceStrength,
    RevisionChangeSource,
    RevisionStatus,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.infrastructure.persistence.strategy_models import (
    ExclusionCriterionRow,
    SearchStrategyRevisionRow,
    SearchStrategyRow,
    SearchThemeRow,
    StrategyCriterionRow,
)


def search_strategy_to_row(entity: SearchStrategy) -> SearchStrategyRow:
    if entity.created_at is None or entity.updated_at is None:
        raise ValueError("SearchStrategy persistence requires created_at and updated_at")
    return SearchStrategyRow(
        id=entity.id,
        owner_key=entity.owner_key,
        current_revision_id=entity.current_revision_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def search_strategy_to_domain(row: SearchStrategyRow) -> SearchStrategy:
    return SearchStrategy(
        id=row.id,
        owner_key=row.owner_key,
        current_revision_id=row.current_revision_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def search_strategy_revision_to_row(
    entity: SearchStrategyRevision,
) -> SearchStrategyRevisionRow:
    return SearchStrategyRevisionRow(
        id=entity.id,
        search_strategy_id=entity.search_strategy_id,
        revision_number=entity.revision_number,
        status=entity.status.value,
        created_at=entity.created_at,
        change_summary=entity.change_summary,
        change_source=entity.change_source.value,
        supersedes_revision_id=entity.supersedes_revision_id,
        content_hash=entity.content_hash,
    )


def search_strategy_revision_to_domain(
    row: SearchStrategyRevisionRow,
) -> SearchStrategyRevision:
    return SearchStrategyRevision(
        id=row.id,
        search_strategy_id=row.search_strategy_id,
        revision_number=row.revision_number,
        status=RevisionStatus(row.status),
        created_at=row.created_at,
        change_summary=row.change_summary,
        change_source=RevisionChangeSource(row.change_source),
        supersedes_revision_id=row.supersedes_revision_id,
        content_hash=row.content_hash,
    )


def search_theme_to_row(entity: SearchTheme) -> SearchThemeRow:
    return SearchThemeRow(
        id=entity.id,
        revision_id=entity.revision_id,
        theme_key=entity.theme_key,
        label=entity.label,
        strength=entity.strength.value,
        is_active=entity.is_active,
        notes=entity.notes,
        sort_order=entity.sort_order,
    )


def search_theme_to_domain(row: SearchThemeRow) -> SearchTheme:
    return SearchTheme(
        id=row.id,
        revision_id=row.revision_id,
        theme_key=row.theme_key,
        label=row.label,
        strength=PreferenceStrength(row.strength),
        is_active=row.is_active,
        notes=row.notes,
        sort_order=row.sort_order,
    )


def strategy_criterion_to_row(entity: StrategyCriterion) -> StrategyCriterionRow:
    return StrategyCriterionRow(
        id=entity.id,
        revision_id=entity.revision_id,
        category=entity.category.value,
        code=entity.code.value,
        value=criterion_value_to_mapping(entity.value),
        strength=entity.strength.value if entity.strength is not None else None,
        is_active=entity.is_active,
        notes=entity.notes,
        sort_order=entity.sort_order,
    )


def strategy_criterion_to_domain(row: StrategyCriterionRow) -> StrategyCriterion:
    category = StrategyCriterionCategory(row.category)
    code = StrategyParameterCode(row.code)
    raw_value = row.value
    if not isinstance(raw_value, dict):
        raise ValueError("strategy_criteria.value must be a JSON object")
    parsed_value = parse_criterion_value(category, code, raw_value)
    strength = (
        PreferenceStrength(row.strength) if row.strength is not None else None
    )
    return StrategyCriterion(
        id=row.id,
        revision_id=row.revision_id,
        category=category,
        code=code,
        value=parsed_value,
        strength=strength,
        is_active=row.is_active,
        notes=row.notes,
        sort_order=row.sort_order,
    )


def exclusion_criterion_to_row(entity: ExclusionCriterion) -> ExclusionCriterionRow:
    return ExclusionCriterionRow(
        id=entity.id,
        revision_id=entity.revision_id,
        exclusion_code=entity.exclusion_code.value,
        parameters=entity.parameters,
        is_active=entity.is_active,
        notes=entity.notes,
    )


def exclusion_criterion_to_domain(row: ExclusionCriterionRow) -> ExclusionCriterion:
    params: dict[str, Any] | None
    if row.parameters is None:
        params = None
    elif isinstance(row.parameters, dict):
        params = dict(row.parameters)
    else:
        raise ValueError("exclusion_criteria.parameters must be a JSON object or null")
    return ExclusionCriterion(
        id=row.id,
        revision_id=row.revision_id,
        exclusion_code=ExclusionCode(row.exclusion_code),
        parameters=params,
        is_active=row.is_active,
        notes=row.notes,
    )
