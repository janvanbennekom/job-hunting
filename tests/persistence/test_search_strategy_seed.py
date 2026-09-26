"""Integration tests for search strategy seeding (Phase 4B)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.infrastructure.importers.search_strategy import SearchStrategySeeder
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRevisionRepository,
)
from jobhunter.infrastructure.persistence.strategy_models import (
    ExclusionCriterionRow,
    SearchStrategyRow,
    SearchThemeRow,
    StrategyCriterionRow,
)

pytestmark = pytest.mark.integration

SYNTH = Path(__file__).resolve().parents[1] / "seeds" / "synthetic_search_strategy.json"


def test_dry_run_does_not_persist(db_session: Session) -> None:
    before = db_session.scalar(select(func.count()).select_from(SearchStrategyRow)) or 0
    report = SearchStrategySeeder(db_session).run(SYNTH, apply=False)
    assert not report.has_errors()
    after = db_session.scalar(select(func.count()).select_from(SearchStrategyRow)) or 0
    assert before == after
    assert report.created_new_revision


def test_apply_and_idempotent_rerun(db_session: Session) -> None:
    seeder = SearchStrategySeeder(db_session)
    first = seeder.run(SYNTH, apply=True)
    assert not first.has_errors()
    assert first.applied
    assert first.revision_id is not None

    second = seeder.run(SYNTH, apply=True)
    assert not second.has_errors()
    assert second.no_op

    assert first.search_strategy_id is not None
    revisions = SearchStrategyRevisionRepository(db_session).list_for_strategy(
        first.search_strategy_id
    )
    assert len(revisions) == 1
    rev_id = revisions[0].id
    themes = (
        db_session.scalar(
            select(func.count())
            .select_from(SearchThemeRow)
            .where(SearchThemeRow.revision_id == rev_id)
        )
        or 0
    )
    criteria = (
        db_session.scalar(
            select(func.count())
            .select_from(StrategyCriterionRow)
            .where(StrategyCriterionRow.revision_id == rev_id)
        )
        or 0
    )
    exclusions = (
        db_session.scalar(
            select(func.count())
            .select_from(ExclusionCriterionRow)
            .where(ExclusionCriterionRow.revision_id == rev_id)
        )
        or 0
    )
    assert themes == 1
    assert criteria == 1
    assert exclusions == 1
