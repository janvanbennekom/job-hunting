"""Repositories for search strategy persistence (Phase 4A.2)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain import (
    ExclusionCriterion,
    RevisionStatus,
    SearchStrategy,
    SearchStrategyRevision,
    SearchTheme,
    StrategyCriterion,
)
from jobhunter.infrastructure.persistence import strategy_mappers as mappers
from jobhunter.infrastructure.persistence.strategy_models import (
    ExclusionCriterionRow,
    SearchStrategyRevisionRow,
    SearchStrategyRow,
    SearchThemeRow,
    StrategyCriterionRow,
)


@dataclass(frozen=True, slots=True)
class PersistedRevisionSnapshot:
    """Read model: one revision and its owned content (not a domain aggregate)."""

    revision: SearchStrategyRevision
    themes: list[SearchTheme]
    criteria: list[StrategyCriterion]
    exclusions: list[ExclusionCriterion]


class SearchStrategyRepository:
    """Mutable strategy identity; supports updating current_revision_id."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: SearchStrategy) -> SearchStrategy:
        row = mappers.search_strategy_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.search_strategy_to_domain(merged)

    def get_by_id(self, entity_id: str) -> SearchStrategy | None:
        row = self._session.get(SearchStrategyRow, entity_id)
        if row is None:
            return None
        return mappers.search_strategy_to_domain(row)

    def get_by_owner_key(self, owner_key: str) -> SearchStrategy | None:
        stmt = select(SearchStrategyRow).where(SearchStrategyRow.owner_key == owner_key)
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.search_strategy_to_domain(row)


class SearchStrategyRevisionRepository:
    """Insert-only for new revision snapshots; use read methods for history."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: SearchStrategyRevision) -> SearchStrategyRevision:
        row = mappers.search_strategy_revision_to_row(entity)
        self._session.add(row)
        self._session.flush()
        return mappers.search_strategy_revision_to_domain(row)

    def get_by_id(self, entity_id: str) -> SearchStrategyRevision | None:
        row = self._session.get(SearchStrategyRevisionRow, entity_id)
        if row is None:
            return None
        return mappers.search_strategy_revision_to_domain(row)

    def get_by_revision_number(
        self, search_strategy_id: str, revision_number: int
    ) -> SearchStrategyRevision | None:
        stmt = select(SearchStrategyRevisionRow).where(
            SearchStrategyRevisionRow.search_strategy_id == search_strategy_id,
            SearchStrategyRevisionRow.revision_number == revision_number,
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.search_strategy_revision_to_domain(row)

    def list_for_strategy(self, search_strategy_id: str) -> list[SearchStrategyRevision]:
        stmt = (
            select(SearchStrategyRevisionRow)
            .where(SearchStrategyRevisionRow.search_strategy_id == search_strategy_id)
            .order_by(SearchStrategyRevisionRow.revision_number)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.search_strategy_revision_to_domain(row) for row in rows]

    def update_status(
        self, revision_id: str, status: RevisionStatus
    ) -> SearchStrategyRevision:
        row = self._session.get(SearchStrategyRevisionRow, revision_id)
        if row is None:
            raise ValueError(f"revision {revision_id} not found")
        row.status = status.value
        self._session.flush()
        return mappers.search_strategy_revision_to_domain(row)


class SearchThemeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: SearchTheme) -> SearchTheme:
        row = mappers.search_theme_to_row(entity)
        self._session.add(row)
        self._session.flush()
        return mappers.search_theme_to_domain(row)

    def list_for_revision(self, revision_id: str) -> list[SearchTheme]:
        stmt = (
            select(SearchThemeRow)
            .where(SearchThemeRow.revision_id == revision_id)
            .order_by(SearchThemeRow.sort_order, SearchThemeRow.theme_key)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.search_theme_to_domain(row) for row in rows]


class StrategyCriterionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: StrategyCriterion) -> StrategyCriterion:
        row = mappers.strategy_criterion_to_row(entity)
        self._session.add(row)
        self._session.flush()
        return mappers.strategy_criterion_to_domain(row)

    def list_for_revision(self, revision_id: str) -> list[StrategyCriterion]:
        stmt = (
            select(StrategyCriterionRow)
            .where(StrategyCriterionRow.revision_id == revision_id)
            .order_by(StrategyCriterionRow.sort_order, StrategyCriterionRow.code)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.strategy_criterion_to_domain(row) for row in rows]


class ExclusionCriterionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ExclusionCriterion) -> ExclusionCriterion:
        row = mappers.exclusion_criterion_to_row(entity)
        self._session.add(row)
        self._session.flush()
        return mappers.exclusion_criterion_to_domain(row)

    def list_for_revision(self, revision_id: str) -> list[ExclusionCriterion]:
        stmt = (
            select(ExclusionCriterionRow)
            .where(ExclusionCriterionRow.revision_id == revision_id)
            .order_by(ExclusionCriterionRow.exclusion_code)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.exclusion_criterion_to_domain(row) for row in rows]


class StrategyRevisionSnapshotRepository:
    """Loads persisted revision content for read/inspection."""

    def __init__(self, session: Session) -> None:
        self._revisions = SearchStrategyRevisionRepository(session)
        self._themes = SearchThemeRepository(session)
        self._criteria = StrategyCriterionRepository(session)
        self._exclusions = ExclusionCriterionRepository(session)

    def load_snapshot(self, revision_id: str) -> PersistedRevisionSnapshot | None:
        revision = self._revisions.get_by_id(revision_id)
        if revision is None:
            return None
        return PersistedRevisionSnapshot(
            revision=revision,
            themes=self._themes.list_for_revision(revision_id),
            criteria=self._criteria.list_for_revision(revision_id),
            exclusions=self._exclusions.list_for_revision(revision_id),
        )
