"""Active search strategy context for read-only dashboard queries."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.strategy_repositories import (
    PersistedRevisionSnapshot,
    SearchStrategyRepository,
    StrategyRevisionSnapshotRepository,
)


@dataclass(frozen=True, slots=True)
class ActiveSearchStrategyContext:
    revision_id: str
    snapshot: PersistedRevisionSnapshot


class ActiveSearchStrategyResolver:
    def __init__(self, session: Session) -> None:
        self._strategies = SearchStrategyRepository(session)
        self._snapshots = StrategyRevisionSnapshotRepository(session)

    def resolve(self, owner_key: str = PRIMARY_PROFILE_KEY) -> ActiveSearchStrategyContext:
        strategy = self._strategies.get_by_owner_key(owner_key)
        if strategy is None or strategy.current_revision_id is None:
            raise RuntimeError(
                f"No active search strategy revision for owner {owner_key!r}"
            )
        snapshot = self._snapshots.load_snapshot(strategy.current_revision_id)
        if snapshot is None:
            raise RuntimeError(
                f"Search strategy revision {strategy.current_revision_id} not found"
            )
        return ActiveSearchStrategyContext(
            revision_id=strategy.current_revision_id,
            snapshot=snapshot,
        )
