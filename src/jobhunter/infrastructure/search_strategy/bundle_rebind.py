"""Rebind revision-owned content to a canonical revision id."""

from __future__ import annotations

from jobhunter.domain.exclusion_criterion import ExclusionCriterion
from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.domain.search_theme import SearchTheme
from jobhunter.domain.strategy_criterion import StrategyCriterion
from jobhunter.domain.strategy_content_hash import compute_revision_content_hash
from jobhunter.infrastructure.search_strategy.identity import (
    exclusion_criterion_id,
    revision_id_for_content,
    strategy_criterion_id,
    theme_id,
)


def rebind_bundle(
    bundle: RevisionContentBundle, revision_id: str
) -> RevisionContentBundle:
    themes = tuple(
        SearchTheme(
            id=theme_id(revision_id, theme.theme_key),
            revision_id=revision_id,
            theme_key=theme.theme_key,
            label=theme.label,
            strength=theme.strength,
            is_active=theme.is_active,
            notes=theme.notes,
            sort_order=theme.sort_order,
        )
        for theme in bundle.themes
    )
    criteria = tuple(
        StrategyCriterion(
            id=strategy_criterion_id(
                revision_id, criterion.category.value, criterion.code.value
            ),
            revision_id=revision_id,
            category=criterion.category,
            code=criterion.code,
            value=criterion.value,
            strength=criterion.strength,
            is_active=criterion.is_active,
            notes=criterion.notes,
            sort_order=criterion.sort_order,
        )
        for criterion in bundle.criteria
    )
    exclusions = tuple(
        ExclusionCriterion(
            id=exclusion_criterion_id(revision_id, exclusion.exclusion_code.value),
            revision_id=revision_id,
            exclusion_code=exclusion.exclusion_code,
            parameters=exclusion.parameters,
            is_active=exclusion.is_active,
            notes=exclusion.notes,
        )
        for exclusion in bundle.exclusions
    )
    return RevisionContentBundle(
        themes=themes, criteria=criteria, exclusions=exclusions
    )


def finalize_bundle_for_strategy(
    search_strategy_id: str,
    bundle: RevisionContentBundle,
) -> tuple[RevisionContentBundle, str]:
    content_hash = compute_revision_content_hash(bundle)
    revision_id = revision_id_for_content(search_strategy_id, content_hash)
    return rebind_bundle(bundle, revision_id), content_hash
