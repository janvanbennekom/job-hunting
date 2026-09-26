"""Canonical strategy content hash tests."""

from __future__ import annotations

from jobhunter.domain import (
    ExclusionCode,
    ExclusionCriterion,
    PreferenceStrength,
    SearchTheme,
    StrategyCriterion,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.domain.strategy_content_hash import compute_revision_content_hash
from jobhunter.domain.strategy_criterion_values import parse_criterion_value


def test_content_hash_stable_for_same_bundle() -> None:
    bundle = _sample_bundle("rev-1")
    assert compute_revision_content_hash(bundle) == compute_revision_content_hash(
        _sample_bundle("rev-2")
    )


def test_content_hash_changes_when_theme_strength_changes() -> None:
    base = _sample_bundle("rev")
    changed = RevisionContentBundle(
        themes=(
            SearchTheme(
                revision_id="rev",
                theme_key="lis",
                label="LIS",
                strength=PreferenceStrength.STRONGLY_PREFERRED,
            ),
        ),
        criteria=base.criteria,
        exclusions=base.exclusions,
    )
    assert compute_revision_content_hash(base) != compute_revision_content_hash(changed)


def _sample_bundle(revision_id: str) -> RevisionContentBundle:
    return RevisionContentBundle(
        themes=(
            SearchTheme(
                revision_id=revision_id,
                theme_key="lis",
                label="LIS",
                strength=PreferenceStrength.PREFERRED,
            ),
        ),
        criteria=(
            StrategyCriterion(
                revision_id=revision_id,
                category=StrategyCriterionCategory.PREFERENCE,
                code=StrategyParameterCode.TRAVEL_PATTERN,
                value=parse_criterion_value(
                    StrategyCriterionCategory.PREFERENCE,
                    StrategyParameterCode.TRAVEL_PATTERN,
                    {"aspect": "continuous_abroad"},
                ),
                strength=PreferenceStrength.LESS_PREFERRED,
            ),
        ),
        exclusions=(
            ExclusionCriterion(
                revision_id=revision_id,
                exclusion_code=ExclusionCode.VOLUNTEER,
            ),
        ),
    )
