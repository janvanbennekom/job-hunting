"""PostgreSQL integration tests for search strategy persistence."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from jobhunter.infrastructure.persistence.profile_models import ProfessionalProfileRow
from jobhunter.infrastructure.persistence.strategy_models import (
    SearchStrategyRow,
    StrategyCriterionRow,
)
from jobhunter.infrastructure.persistence.strategy_repositories import (
    ExclusionCriterionRepository,
    SearchStrategyRepository,
    SearchStrategyRevisionRepository,
    SearchThemeRepository,
    StrategyCriterionRepository,
    StrategyRevisionSnapshotRepository,
)

pytestmark = pytest.mark.integration

UTC = timezone.utc
HASH = "a" * 64


def _ts() -> datetime:
    return datetime(2026, 9, 26, 14, 0, tzinfo=UTC)


def _strategy(owner: str = "synthetic-owner") -> SearchStrategy:
    return SearchStrategy(
        id="strategy-synth-1",
        owner_key=owner,
        current_revision_id=None,
        created_at=_ts(),
        updated_at=_ts(),
    )


def _revision(
    strategy_id: str,
    number: int,
    *,
    rev_id: str,
    supersedes: str | None = None,
) -> SearchStrategyRevision:
    return SearchStrategyRevision(
        id=rev_id,
        search_strategy_id=strategy_id,
        revision_number=number,
        status=RevisionStatus.ACTIVE if number == 1 else RevisionStatus.SUPERSEDED,
        created_at=_ts(),
        change_summary=f"Revision {number}",
        change_source=RevisionChangeSource.INITIAL_SEED,
        supersedes_revision_id=supersedes,
        content_hash=HASH,
    )


def test_search_strategy_save_and_owner_lookup(db_session: Session) -> None:
    repo = SearchStrategyRepository(db_session)
    entity = _strategy()
    saved = repo.save(entity)
    assert saved.current_revision_id is None
    loaded = repo.get_by_owner_key("synthetic-owner")
    assert loaded == saved


def test_search_strategy_owner_key_unique(db_session: Session) -> None:
    repo = SearchStrategyRepository(db_session)
    repo.save(_strategy())
    with pytest.raises(IntegrityError):
        repo.save(
            SearchStrategy(
                id="strategy-synth-2",
                owner_key="synthetic-owner",
                created_at=_ts(),
                updated_at=_ts(),
            )
        )


def test_revision_list_order_and_unique_number(db_session: Session) -> None:
    strategies = SearchStrategyRepository(db_session)
    revisions = SearchStrategyRevisionRepository(db_session)
    strategies.save(_strategy())
    revisions.add(_revision("strategy-synth-1", 1, rev_id="rev-1"))
    revisions.add(
        _revision("strategy-synth-1", 2, rev_id="rev-2", supersedes="rev-1")
    )
    listed = revisions.list_for_strategy("strategy-synth-1")
    assert [r.revision_number for r in listed] == [1, 2]
    with pytest.raises(IntegrityError):
        revisions.add(_revision("strategy-synth-1", 2, rev_id="rev-dup"))


def test_theme_unique_per_revision(db_session: Session) -> None:
    SearchStrategyRepository(db_session).save(_strategy())
    SearchStrategyRevisionRepository(db_session).add(
        _revision("strategy-synth-1", 1, rev_id="rev-1")
    )
    themes = SearchThemeRepository(db_session)
    themes.add(
        SearchTheme(
            id="theme-1",
            revision_id="rev-1",
            theme_key="lis",
            label="LIS",
            strength=PreferenceStrength.STRONGLY_PREFERRED,
        )
    )
    with pytest.raises(IntegrityError):
        themes.add(
            SearchTheme(
                id="theme-2",
                revision_id="rev-1",
                theme_key="lis",
                label="Duplicate",
                strength=PreferenceStrength.PREFERRED,
            )
        )


def test_strategy_criterion_jsonb_typed_round_trip(db_session: Session) -> None:
    SearchStrategyRepository(db_session).save(_strategy())
    SearchStrategyRevisionRepository(db_session).add(
        _revision("strategy-synth-1", 1, rev_id="rev-1")
    )
    criteria = StrategyCriterionRepository(db_session)
    travel = StrategyCriterion(
        id="crit-travel",
        revision_id="rev-1",
        category=StrategyCriterionCategory.PREFERENCE,
        code=StrategyParameterCode.TRAVEL_PATTERN,
        value=parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.TRAVEL_PATTERN,
            {"aspect": "continuous_abroad"},
        ),
        strength=PreferenceStrength.LESS_PREFERRED,
    )
    criteria.add(travel)
    geo = StrategyCriterion(
        id="crit-geo",
        revision_id="rev-1",
        category=StrategyCriterionCategory.PREFERENCE,
        code=StrategyParameterCode.GEOGRAPHY,
        value=parse_criterion_value(
            StrategyCriterionCategory.PREFERENCE,
            StrategyParameterCode.GEOGRAPHY,
            {
                "regions": [{"name": "Africa", "strength": "PREFERRED"}],
                "countries": [],
            },
        ),
    )
    criteria.add(geo)
    hard = StrategyCriterion(
        id="crit-hard",
        revision_id="rev-1",
        category=StrategyCriterionCategory.HARD_CONSTRAINT,
        code=StrategyParameterCode.ASSIGNMENT_DURATION,
        value=parse_criterion_value(
            StrategyCriterionCategory.HARD_CONSTRAINT,
            StrategyParameterCode.ASSIGNMENT_DURATION,
            {"max_months": 18},
        ),
    )
    criteria.add(hard)
    loaded = criteria.list_for_revision("rev-1")
    assert len(loaded) == 3
    by_id = {c.id: c for c in loaded}
    assert by_id["crit-travel"].strength is PreferenceStrength.LESS_PREFERRED
    assert by_id["crit-hard"].strength is None


def test_strategy_criterion_unique_category_code(db_session: Session) -> None:
    SearchStrategyRepository(db_session).save(_strategy())
    SearchStrategyRevisionRepository(db_session).add(
        _revision("strategy-synth-1", 1, rev_id="rev-1")
    )
    repo = StrategyCriterionRepository(db_session)
    value = parse_criterion_value(
        StrategyCriterionCategory.PREFERENCE,
        StrategyParameterCode.TRAVEL_PATTERN,
        {"aspect": "continuous_abroad"},
    )
    repo.add(
        StrategyCriterion(
            revision_id="rev-1",
            category=StrategyCriterionCategory.PREFERENCE,
            code=StrategyParameterCode.TRAVEL_PATTERN,
            value=value,
            strength=PreferenceStrength.LESS_PREFERRED,
        )
    )
    with pytest.raises(IntegrityError):
        repo.add(
            StrategyCriterion(
                id="crit-dup",
                revision_id="rev-1",
                category=StrategyCriterionCategory.PREFERENCE,
                code=StrategyParameterCode.TRAVEL_PATTERN,
                value=value,
                strength=PreferenceStrength.PREFERRED,
            )
        )


def test_malformed_criterion_json_fails_on_load(db_session: Session) -> None:
    SearchStrategyRepository(db_session).save(_strategy())
    SearchStrategyRevisionRepository(db_session).add(
        _revision("strategy-synth-1", 1, rev_id="rev-1")
    )
    db_session.add(
        StrategyCriterionRow(
            id="crit-bad",
            revision_id="rev-1",
            category=StrategyCriterionCategory.PREFERENCE.value,
            code=StrategyParameterCode.WORK_MODE.value,
            value={"remote": "PREFERRED"},
            strength=None,
            is_active=True,
            sort_order=0,
        )
    )
    db_session.flush()
    with pytest.raises(ValueError, match="WORK_MODE requires"):
        StrategyCriterionRepository(db_session).list_for_revision("rev-1")


def test_exclusion_unique_per_revision(db_session: Session) -> None:
    SearchStrategyRepository(db_session).save(_strategy())
    SearchStrategyRevisionRepository(db_session).add(
        _revision("strategy-synth-1", 1, rev_id="rev-1")
    )
    repo = ExclusionCriterionRepository(db_session)
    repo.add(
        ExclusionCriterion(
            id="ex-1",
            revision_id="rev-1",
            exclusion_code=ExclusionCode.VOLUNTEER,
        )
    )
    with pytest.raises(IntegrityError):
        repo.add(
            ExclusionCriterion(
                id="ex-2",
                revision_id="rev-1",
                exclusion_code=ExclusionCode.VOLUNTEER,
            )
        )


def test_two_revisions_preserve_historical_content(db_session: Session) -> None:
    SearchStrategyRepository(db_session).save(_strategy())
    rev_repo = SearchStrategyRevisionRepository(db_session)
    themes = SearchThemeRepository(db_session)
    snapshots = StrategyRevisionSnapshotRepository(db_session)
    rev_repo.add(_revision("strategy-synth-1", 1, rev_id="rev-1"))
    themes.add(
        SearchTheme(
            id="t1",
            revision_id="rev-1",
            theme_key="lis",
            label="LIS v1",
            strength=PreferenceStrength.PREFERRED,
        )
    )
    rev_repo.add(
        _revision("strategy-synth-1", 2, rev_id="rev-2", supersedes="rev-1")
    )
    themes.add(
        SearchTheme(
            id="t2",
            revision_id="rev-2",
            theme_key="gis",
            label="GIS v2",
            strength=PreferenceStrength.ACCEPTABLE,
        )
    )
    snap1 = snapshots.load_snapshot("rev-1")
    snap2 = snapshots.load_snapshot("rev-2")
    assert snap1 is not None and snap2 is not None
    assert snap1.themes[0].label == "LIS v1"
    assert snap2.themes[0].theme_key == "gis"


def test_professional_profile_tables_unaffected(db_session: Session) -> None:
    before = (
        db_session.scalar(select(func.count()).select_from(ProfessionalProfileRow)) or 0
    )
    SearchStrategyRepository(db_session).save(_strategy())
    after = (
        db_session.scalar(select(func.count()).select_from(ProfessionalProfileRow)) or 0
    )
    assert before == after


def test_no_strategy_rows_without_test_insert(db_session: Session) -> None:
    """Sanity: other tests roll back; count is zero before local inserts."""
    count = (
        db_session.scalar(select(func.count()).select_from(SearchStrategyRow)) or 0
    )
    assert count == 0
