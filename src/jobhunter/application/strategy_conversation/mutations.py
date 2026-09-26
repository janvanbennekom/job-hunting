"""Apply structured strategy mutations to a revision content bundle."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from jobhunter.domain.exclusion_criterion import ExclusionCriterion
from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.domain.search_theme import SearchTheme
from jobhunter.domain.strategy_criterion import StrategyCriterion
from jobhunter.domain.strategy_criterion_values import (
    criterion_value_to_mapping,
    parse_criterion_value,
)
from jobhunter.domain.strategy_enums import (
    ExclusionCode,
    PreferenceStrength,
    StrategyCriterionCategory,
    StrategyParameterCode,
)


class MutationApplyError(Exception):
    pass


def apply_mutations(
    bundle: RevisionContentBundle,
    mutations: list[dict[str, Any]],
) -> RevisionContentBundle:
    themes = {theme.theme_key: theme for theme in bundle.themes}
    criteria = {
        (criterion.category, criterion.code): criterion for criterion in bundle.criteria
    }
    exclusions = {
        exclusion.exclusion_code: exclusion for exclusion in bundle.exclusions
    }
    errors: list[str] = []

    for index, mutation in enumerate(mutations):
        op = mutation.get("op")
        try:
            if op == "SET_THEME_STRENGTH":
                _set_theme_strength(themes, mutation)
            elif op == "SET_THEME_ACTIVE":
                _set_theme_active(themes, mutation)
            elif op == "SET_CRITERION":
                _set_criterion(criteria, mutation, bundle)
            elif op == "SET_EXCLUSION_ACTIVE":
                _set_exclusion_active(exclusions, mutation, bundle)
            elif op == "UPSERT_GEOGRAPHY_PLACE":
                _upsert_geography(criteria, mutation, bundle)
            else:
                errors.append(f"mutation[{index}]: unknown op {op!r}")
        except (MutationApplyError, ValueError, KeyError) as exc:
            errors.append(f"mutation[{index}]: {exc}")

    if errors:
        raise MutationApplyError("; ".join(errors))

    return RevisionContentBundle(
        themes=tuple(themes.values()),
        criteria=tuple(criteria.values()),
        exclusions=tuple(exclusions.values()),
    )


def _set_theme_strength(themes: dict[str, SearchTheme], mutation: dict[str, Any]) -> None:
    key = mutation.get("theme_key")
    strength = mutation.get("strength")
    if not key or not strength:
        raise MutationApplyError("SET_THEME_STRENGTH requires theme_key and strength")
    theme = themes.get(str(key))
    if theme is None:
        raise MutationApplyError(f"unknown theme_key {key!r}")
    themes[key] = SearchTheme(
        id=theme.id,
        revision_id=theme.revision_id,
        theme_key=theme.theme_key,
        label=theme.label,
        strength=PreferenceStrength(str(strength)),
        is_active=theme.is_active,
        notes=theme.notes,
        sort_order=theme.sort_order,
    )


def _set_theme_active(themes: dict[str, SearchTheme], mutation: dict[str, Any]) -> None:
    key = mutation.get("theme_key")
    if key is None or "is_active" not in mutation:
        raise MutationApplyError("SET_THEME_ACTIVE requires theme_key and is_active")
    theme = themes.get(str(key))
    if theme is None:
        raise MutationApplyError(f"unknown theme_key {key!r}")
    themes[key] = SearchTheme(
        id=theme.id,
        revision_id=theme.revision_id,
        theme_key=theme.theme_key,
        label=theme.label,
        strength=theme.strength,
        is_active=bool(mutation["is_active"]),
        notes=theme.notes,
        sort_order=theme.sort_order,
    )


def _set_criterion(
    criteria: dict[tuple, StrategyCriterion],
    mutation: dict[str, Any],
    bundle: RevisionContentBundle,
) -> None:
    category = StrategyCriterionCategory(str(mutation["category"]))
    code = StrategyParameterCode(str(mutation["code"]))
    value_raw = mutation.get("value")
    if not isinstance(value_raw, dict):
        raise MutationApplyError("SET_CRITERION requires value object")
    value = parse_criterion_value(category, code, value_raw)
    strength_raw = mutation.get("strength")
    strength = (
        PreferenceStrength(str(strength_raw)) if strength_raw is not None else None
    )
    notes = mutation.get("notes")
    key = (category, code)
    existing = criteria.get(key)
    revision_id = existing.revision_id if existing else bundle.themes[0].revision_id
    criterion_id = existing.id if existing else "pending"
    criteria[key] = StrategyCriterion(
        id=criterion_id,
        revision_id=revision_id,
        category=category,
        code=code,
        value=value,
        strength=strength if strength is not None else (existing.strength if existing else None),
        is_active=existing.is_active if existing else True,
        notes=notes if notes is not None else (existing.notes if existing else None),
        sort_order=existing.sort_order if existing else 0,
    )


def _set_exclusion_active(
    exclusions: dict[ExclusionCode, ExclusionCriterion],
    mutation: dict[str, Any],
    bundle: RevisionContentBundle,
) -> None:
    code = ExclusionCode(str(mutation["exclusion_code"]))
    if "is_active" not in mutation:
        raise MutationApplyError("SET_EXCLUSION_ACTIVE requires is_active")
    existing = exclusions.get(code)
    revision_id = (
        existing.revision_id
        if existing
        else (bundle.exclusions[0].revision_id if bundle.exclusions else "pending")
    )
    exclusions[code] = ExclusionCriterion(
        id=existing.id if existing else "pending",
        revision_id=revision_id,
        exclusion_code=code,
        parameters=existing.parameters if existing else None,
        is_active=bool(mutation["is_active"]),
        notes=existing.notes if existing else None,
    )


def _upsert_geography(
    criteria: dict[tuple, StrategyCriterion],
    mutation: dict[str, Any],
    bundle: RevisionContentBundle,
) -> None:
    place_type = str(mutation.get("place_type", "")).lower()
    name = mutation.get("name")
    strength = mutation.get("strength")
    if place_type not in {"region", "country"} or not name or not strength:
        raise MutationApplyError(
            "UPSERT_GEOGRAPHY_PLACE requires place_type, name, strength"
        )
    key = (StrategyCriterionCategory.PREFERENCE, StrategyParameterCode.GEOGRAPHY)
    existing = criteria.get(key)
    if existing is None:
        raise MutationApplyError("GEOGRAPHY preference criterion not found")
    mapping = deepcopy(criterion_value_to_mapping(existing.value))
    list_key = "regions" if place_type == "region" else "countries"
    entries = list(mapping.get(list_key) or [])
    replaced = False
    for item in entries:
        if str(item.get("name", "")).lower() == str(name).lower():
            item["strength"] = str(strength)
            replaced = True
    if not replaced:
        entries.append({"name": str(name), "strength": str(strength)})
    mapping[list_key] = entries
    value = parse_criterion_value(
        StrategyCriterionCategory.PREFERENCE,
        StrategyParameterCode.GEOGRAPHY,
        mapping,
    )
    criteria[key] = StrategyCriterion(
        id=existing.id,
        revision_id=existing.revision_id,
        category=existing.category,
        code=existing.code,
        value=value,
        strength=existing.strength,
        is_active=existing.is_active,
        notes=existing.notes,
        sort_order=existing.sort_order,
    )
