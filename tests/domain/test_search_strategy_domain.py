"""Phase 4A.1 search strategy domain tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from jobhunter.domain import (
    ExclusionCode,
    ExclusionCriterion,
    PreferenceStrength,
    RevisionChangeSource,
    RevisionStatus,
    SearchStrategy,
    SearchStrategyRevision,
    SearchTheme,
    StrategyCriterion,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.domain.strategy_criterion_values import parse_criterion_value

UTC = timezone.utc
VALID_HASH = "a" * 64


def _ts() -> datetime:
    return datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def test_search_strategy_construction_and_round_trip() -> None:
    strategy = SearchStrategy(
        id="strategy-1",
        owner_key="jan-van-bennekom-minnema",
        current_revision_id=None,
        created_at=_ts(),
        updated_at=_ts(),
    )
    assert strategy.current_revision_id is None
    restored = SearchStrategy.from_mapping(strategy.to_mapping())
    assert restored == strategy


def test_search_strategy_rejects_empty_owner_key() -> None:
    with pytest.raises(ValueError, match="owner_key"):
        SearchStrategy(owner_key="  ")


def test_search_strategy_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SearchStrategy(
            owner_key="owner",
            created_at=datetime(2026, 1, 1),
        )


def test_search_strategy_revision_active_and_superseded() -> None:
    rev = SearchStrategyRevision(
        id="rev-1",
        search_strategy_id="strategy-1",
        revision_number=1,
        status=RevisionStatus.ACTIVE,
        created_at=_ts(),
        change_summary="Initial",
        change_source=RevisionChangeSource.INITIAL_SEED,
        content_hash=VALID_HASH,
    )
    assert rev.status is RevisionStatus.ACTIVE
    superseded = SearchStrategyRevision(
        id="rev-0",
        search_strategy_id="strategy-1",
        revision_number=1,
        status=RevisionStatus.SUPERSEDED,
        created_at=_ts(),
        change_summary="Old",
        change_source=RevisionChangeSource.MANUAL,
        content_hash=VALID_HASH,
        supersedes_revision_id=None,
    )
    assert superseded.status is RevisionStatus.SUPERSEDED
    restored = SearchStrategyRevision.from_mapping(rev.to_mapping())
    assert restored == rev


def test_search_strategy_revision_rejects_non_positive_number() -> None:
    with pytest.raises(ValueError, match="positive"):
        SearchStrategyRevision(
            search_strategy_id="s",
            revision_number=0,
            status=RevisionStatus.ACTIVE,
            created_at=_ts(),
            change_summary="x",
            change_source=RevisionChangeSource.MANUAL,
            content_hash=VALID_HASH,
        )


def test_search_strategy_revision_rejects_invalid_content_hash() -> None:
    with pytest.raises(ValueError, match="content_hash"):
        SearchStrategyRevision(
            search_strategy_id="s",
            revision_number=1,
            status=RevisionStatus.ACTIVE,
            created_at=_ts(),
            change_summary="x",
            change_source=RevisionChangeSource.MANUAL,
            content_hash="not-a-hash",
        )


def test_search_theme_all_strengths_and_round_trip() -> None:
    for strength in PreferenceStrength:
        theme = SearchTheme(
            id="theme-1",
            revision_id="rev-1",
            theme_key="lis_implementation",
            label="LIS implementation",
            strength=strength,
            is_active=True,
            sort_order=1,
        )
        assert SearchTheme.from_mapping(theme.to_mapping()) == theme


def test_search_theme_invalid_key_label_order() -> None:
    with pytest.raises(ValueError, match="theme_key"):
        SearchTheme(
            revision_id="r",
            theme_key=" ",
            label="Label",
            strength=PreferenceStrength.PREFERRED,
        )
    with pytest.raises(ValueError, match="label"):
        SearchTheme(
            revision_id="r",
            theme_key="key",
            label=" ",
            strength=PreferenceStrength.PREFERRED,
        )
    with pytest.raises(ValueError, match="sort_order"):
        SearchTheme(
            revision_id="r",
            theme_key="key",
            label="Label",
            strength=PreferenceStrength.PREFERRED,
            sort_order=-1,
        )


def test_search_theme_is_frozen() -> None:
    theme = SearchTheme(
        revision_id="r",
        theme_key="key",
        label="Label",
        strength=PreferenceStrength.PREFERRED,
    )
    with pytest.raises(AttributeError):
        theme.label = "Changed"  # type: ignore[misc]


def test_strategy_criterion_assignment_delivery_mode() -> None:
    criterion = StrategyCriterion(
        id="c-1",
        revision_id="rev-1",
        category=StrategyCriterionCategory.PREFERENCE,
        code=StrategyParameterCode.ASSIGNMENT_DELIVERY_MODE,
        value=parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.ASSIGNMENT_DELIVERY_MODE,
            {
                "implementation": "STRONGLY_PREFERRED",
                "advisory": "ACCEPTABLE",
            },
        ),
    )
    restored = StrategyCriterion.from_mapping(criterion.to_mapping())
    assert restored == criterion


def test_strategy_criterion_travel_pattern_requires_strength() -> None:
    with pytest.raises(ValueError, match="requires criterion-level"):
        StrategyCriterion(
            revision_id="r",
            category=StrategyCriterionCategory.PREFERENCE,
            code=StrategyParameterCode.TRAVEL_PATTERN,
            value=parse_criterion_value(
                StrategyCriterionCategory.PREFERENCE,
                StrategyParameterCode.TRAVEL_PATTERN,
                {"aspect": "continuous_abroad"},
            ),
            strength=None,
        )


def test_strategy_criterion_travel_pattern_preference() -> None:
    criterion = StrategyCriterion(
        revision_id="r",
        category=StrategyCriterionCategory.PREFERENCE,
        code=StrategyParameterCode.TRAVEL_PATTERN,
        value=parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.TRAVEL_PATTERN,
            {"aspect": "continuous_abroad"},
        ),
        strength=PreferenceStrength.LESS_PREFERRED,
    )
    assert StrategyCriterion.from_mapping(criterion.to_mapping()) == criterion


def test_strategy_criterion_hard_constraint_rejects_strength() -> None:
    with pytest.raises(ValueError, match="must not set preference strength"):
        StrategyCriterion(
            revision_id="r",
            category=StrategyCriterionCategory.HARD_CONSTRAINT,
            code=StrategyParameterCode.ASSIGNMENT_DURATION,
            value=parse_criterion_value(
                StrategyCriterionCategory.HARD_CONSTRAINT,
                StrategyParameterCode.ASSIGNMENT_DURATION,
                {"max_months": 12},
            ),
            strength=PreferenceStrength.PREFERRED,
        )


def test_strategy_criterion_geography_constraint() -> None:
    criterion = StrategyCriterion(
        revision_id="r",
        category=StrategyCriterionCategory.HARD_CONSTRAINT,
        code=StrategyParameterCode.GEOGRAPHY,
        value=parse_criterion_value(
            StrategyCriterionCategory.HARD_CONSTRAINT,
            StrategyParameterCode.GEOGRAPHY,
            {"excluded_countries": ["Exampleland"]},
        ),
    )
    assert StrategyCriterion.from_mapping(criterion.to_mapping()) == criterion


def test_strategy_criterion_invalid_value_keys() -> None:
    with pytest.raises(ValueError):
        parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.WORK_MODE,
            {"remote": "PREFERRED", "hybrid": "PREFERRED"},
        )
    with pytest.raises(ValueError, match="aspect"):
        parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.TRAVEL_PATTERN,
            {"aspect": "unknown"},
        )


def test_strategy_criterion_each_parameter_code() -> None:
    samples = [
        (
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.WORK_MODE,
            {
                "remote": "PREFERRED",
                "hybrid": "ACCEPTABLE",
                "on_site": "LESS_PREFERRED",
            },
            None,
        ),
        (
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.GEOGRAPHY,
            {
                "regions": [{"name": "Europe", "strength": "ACCEPTABLE"}],
                "countries": [],
            },
            None,
        ),
        (
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.ASSIGNMENT_DURATION,
            {"ideal_min_months": 3, "ideal_max_months": 12},
            PreferenceStrength.PREFERRED,
        ),
        (
            StrategyCriterionCategory.HARD_CONSTRAINT,
            StrategyParameterCode.ASSIGNMENT_DURATION,
            {"max_months": 24},
            None,
        ),
        (
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.ENGAGEMENT_MODEL,
            {
                "international_consultancy": "STRONGLY_PREFERRED",
                "single_consultant_engagement": "PREFERRED",
            },
            None,
        ),
        (
            StrategyCriterionCategory.HARD_CONSTRAINT,
            StrategyParameterCode.ENGAGEMENT_MODEL,
            {"single_consultant_only": True},
            None,
        ),
    ]
    for category, code, value, strength in samples:
        criterion = StrategyCriterion(
            revision_id="r",
            category=category,
            code=code,
            value=parse_criterion_value(category, code, value),
            strength=strength,
        )
        assert StrategyCriterion.from_mapping(criterion.to_mapping()) == criterion


def test_exclusion_criterion_round_trip() -> None:
    exclusion = ExclusionCriterion(
        id="e-1",
        revision_id="rev-1",
        exclusion_code=ExclusionCode.REQUIRES_MULTI_PERSON_TEAM_OR_CONSORTIUM,
        is_active=True,
        notes="Synthetic",
    )
    restored = ExclusionCriterion.from_mapping(exclusion.to_mapping())
    assert restored == exclusion


def test_exclusion_criterion_rejects_parameters_in_mvp() -> None:
    with pytest.raises(ValueError, match="does not accept parameters"):
        ExclusionCriterion(
            revision_id="r",
            exclusion_code=ExclusionCode.VOLUNTEER,
            parameters={"unexpected": True},
        )


def test_independence_from_professional_profile() -> None:
    """Domain imports must not pull in professional evidence types."""
    import jobhunter.domain.search_strategy as ss_mod

    source = open(ss_mod.__file__, encoding="utf-8").read()
    assert "ProfessionalProfile" not in source
    assert "sqlalchemy" not in source.lower()


def test_geography_preference_per_place_strengths() -> None:
    criterion = StrategyCriterion(
        revision_id="r",
        category=StrategyCriterionCategory.PREFERENCE,
        code=StrategyParameterCode.GEOGRAPHY,
        value=parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.GEOGRAPHY,
            {
                "regions": [
                    {"name": "Africa", "strength": "PREFERRED"},
                    {"name": "Middle East", "strength": "PREFERRED"},
                    {"name": "Europe", "strength": "ACCEPTABLE"},
                ],
                "countries": [
                    {"name": "Timor-Leste", "strength": "STRONGLY_PREFERRED"},
                ],
            },
        ),
    )
    assert StrategyCriterion.from_mapping(criterion.to_mapping()) == criterion
    with pytest.raises(ValueError, match="unknown keys"):
        parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.GEOGRAPHY,
            {
                "regions": [],
                "preferred_countries": ["Legacy"],
            },
        )
    with pytest.raises(ValueError, match="unknown keys"):
        parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.GEOGRAPHY,
            {
                "regions": [{"name": "Africa", "strength": "PREFERRED", "weight": 1}],
                "countries": [],
            },
        )


def test_geography_preference_rejects_criterion_level_strength() -> None:
    value = parse_criterion_value(
        StrategyCriterionCategory.PREFERENCE,
        StrategyParameterCode.GEOGRAPHY,
        {"regions": [{"name": "Africa", "strength": "PREFERRED"}], "countries": []},
    )
    with pytest.raises(ValueError, match="structured value"):
        StrategyCriterion(
            revision_id="r",
            category=StrategyCriterionCategory.PREFERENCE,
            code=StrategyParameterCode.GEOGRAPHY,
            value=value,
            strength=PreferenceStrength.PREFERRED,
        )


def test_assignment_duration_constraint_requires_bounds() -> None:
    with pytest.raises(ValueError, match="min_months or max_months"):
        parse_criterion_value(
            StrategyCriterionCategory.HARD_CONSTRAINT,
            StrategyParameterCode.ASSIGNMENT_DURATION,
            {},
        )
