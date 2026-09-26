"""Read-only strategy inspection for UI."""

from __future__ import annotations

from sqlalchemy.orm import Session

from jobhunter.application.strategy_conversation.context import (
    snapshot_to_interpretation_context,
)
from jobhunter.application.strategy_conversation.dtos import (
    ActiveStrategyView,
    StrategyRevisionSummary,
)
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
    SearchStrategyRevisionRepository,
    StrategyRevisionSnapshotRepository,
)


class StrategyQueryService:
    def __init__(self, session: Session) -> None:
        self._strategies = SearchStrategyRepository(session)
        self._revisions = SearchStrategyRevisionRepository(session)
        self._snapshots = StrategyRevisionSnapshotRepository(session)

    def get_active_view(
        self, owner_key: str = PRIMARY_PROFILE_KEY
    ) -> ActiveStrategyView | None:
        strategy = self._strategies.get_by_owner_key(owner_key)
        if strategy is None:
            return None
        if strategy.current_revision_id is None:
            return ActiveStrategyView(
                owner_key=owner_key,
                strategy_id=strategy.id,
                current_revision_id=None,
                revision_number=None,
                change_summary=None,
                content_hash=None,
                themes=[],
                criteria=[],
                exclusions=[],
            )
        snapshot = self._snapshots.load_snapshot(strategy.current_revision_id)
        if snapshot is None:
            return None
        context = snapshot_to_interpretation_context(snapshot)
        return ActiveStrategyView(
            owner_key=owner_key,
            strategy_id=strategy.id,
            current_revision_id=snapshot.revision.id,
            revision_number=snapshot.revision.revision_number,
            change_summary=snapshot.revision.change_summary,
            content_hash=snapshot.revision.content_hash,
            themes=context["themes"],
            criteria=context["criteria"],
            exclusions=context["exclusions"],
        )

    def list_revision_history(
        self, owner_key: str = PRIMARY_PROFILE_KEY
    ) -> list[StrategyRevisionSummary]:
        strategy = self._strategies.get_by_owner_key(owner_key)
        if strategy is None:
            return []
        revisions = self._revisions.list_for_strategy(strategy.id)
        return [
            StrategyRevisionSummary(
                revision_id=revision.id,
                revision_number=revision.revision_number,
                status=revision.status.value,
                created_at=revision.created_at.isoformat(),
                change_summary=revision.change_summary,
                change_source=revision.change_source.value,
                content_hash=revision.content_hash,
                is_current=revision.id == strategy.current_revision_id,
            )
            for revision in revisions
        ]
