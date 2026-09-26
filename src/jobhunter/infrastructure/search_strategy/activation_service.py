"""Activate search strategy revisions (Phase 4A.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.domain import (
    RevisionChangeSource,
    RevisionStatus,
    SearchStrategy,
    SearchStrategyRevision,
)
from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.domain.strategy_content_hash import compute_revision_content_hash
from jobhunter.infrastructure.persistence.strategy_repositories import (
    ExclusionCriterionRepository,
    SearchStrategyRepository,
    SearchStrategyRevisionRepository,
    SearchThemeRepository,
    StrategyCriterionRepository,
    StrategyRevisionSnapshotRepository,
)
from jobhunter.infrastructure.search_strategy.identity import (
    revision_id_for_content,
    search_strategy_id,
)


@dataclass(frozen=True, slots=True)
class ActivationResult:
    search_strategy_id: str
    revision_id: str | None
    content_hash: str
    created_new_revision: bool
    reactivated_existing_revision: bool
    no_op: bool


class SearchStrategyActivationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._strategies = SearchStrategyRepository(session)
        self._revisions = SearchStrategyRevisionRepository(session)
        self._themes = SearchThemeRepository(session)
        self._criteria = StrategyCriterionRepository(session)
        self._exclusions = ExclusionCriterionRepository(session)
        self._snapshots = StrategyRevisionSnapshotRepository(session)

    def activate(
        self,
        owner_key: str,
        bundle: RevisionContentBundle,
        *,
        change_summary: str,
        change_source: RevisionChangeSource,
        apply: bool = True,
    ) -> ActivationResult:
        content_hash = compute_revision_content_hash(bundle)
        strategy = self._strategies.get_by_owner_key(owner_key)
        strategy_id = strategy.id if strategy is not None else search_strategy_id(owner_key)
        revision_id = revision_id_for_content(strategy_id, content_hash)

        current = self._current_revision(strategy) if strategy is not None else None
        if current is not None and current.content_hash == content_hash:
            return ActivationResult(
                search_strategy_id=strategy_id,
                revision_id=current.id,
                content_hash=content_hash,
                created_new_revision=False,
                reactivated_existing_revision=False,
                no_op=True,
            )

        existing = self._revisions.get_by_id(revision_id)
        if existing is not None:
            if not apply:
                return ActivationResult(
                    search_strategy_id=strategy_id,
                    revision_id=revision_id,
                    content_hash=content_hash,
                    created_new_revision=False,
                    reactivated_existing_revision=True,
                    no_op=False,
                )
            strategy = self._ensure_strategy(owner_key)
            self._reactivate_revision(strategy, existing)
            return ActivationResult(
                search_strategy_id=strategy.id,
                revision_id=existing.id,
                content_hash=content_hash,
                created_new_revision=False,
                reactivated_existing_revision=True,
                no_op=False,
            )

        if not apply:
            return ActivationResult(
                search_strategy_id=strategy_id,
                revision_id=revision_id,
                content_hash=content_hash,
                created_new_revision=True,
                reactivated_existing_revision=False,
                no_op=False,
            )

        strategy = self._ensure_strategy(owner_key)
        revision_id = revision_id_for_content(strategy.id, content_hash)

        revision = self._create_revision(
            strategy=strategy,
            revision_id=revision_id,
            content_hash=content_hash,
            change_summary=change_summary,
            change_source=change_source,
            supersedes_revision_id=current.id if current else None,
        )
        self._persist_bundle(revision, bundle)
        self._supersede_active_revisions(strategy.id, keep_revision_id=revision.id)
        self._set_current_revision(strategy, revision.id)
        return ActivationResult(
            search_strategy_id=strategy.id,
            revision_id=revision.id,
            content_hash=content_hash,
            created_new_revision=True,
            reactivated_existing_revision=False,
            no_op=False,
        )

    def _ensure_strategy(self, owner_key: str) -> SearchStrategy:
        existing = self._strategies.get_by_owner_key(owner_key)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        strategy = SearchStrategy(
            id=search_strategy_id(owner_key),
            owner_key=owner_key,
            current_revision_id=None,
            created_at=now,
            updated_at=now,
        )
        return self._strategies.save(strategy)

    def _current_revision(
        self, strategy: SearchStrategy | None
    ) -> SearchStrategyRevision | None:
        if strategy is None:
            return None
        if strategy.current_revision_id is None:
            return None
        revision = self._revisions.get_by_id(strategy.current_revision_id)
        if revision is None:
            return None
        if revision.search_strategy_id != strategy.id:
            raise ValueError(
                "current_revision_id points to a revision owned by another strategy"
            )
        return revision

    def _next_revision_number(self, search_strategy_id: str) -> int:
        revisions = self._revisions.list_for_strategy(search_strategy_id)
        if not revisions:
            return 1
        return max(r.revision_number for r in revisions) + 1

    def _create_revision(
        self,
        *,
        strategy: SearchStrategy,
        revision_id: str,
        content_hash: str,
        change_summary: str,
        change_source: RevisionChangeSource,
        supersedes_revision_id: str | None,
    ) -> SearchStrategyRevision:
        revision = SearchStrategyRevision(
            id=revision_id,
            search_strategy_id=strategy.id,
            revision_number=self._next_revision_number(strategy.id),
            status=RevisionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            change_summary=change_summary,
            change_source=change_source,
            supersedes_revision_id=supersedes_revision_id,
            content_hash=content_hash,
        )
        return self._revisions.add(revision)

    def _persist_bundle(
        self, revision: SearchStrategyRevision, bundle: RevisionContentBundle
    ) -> None:
        for theme in bundle.themes:
            if theme.revision_id != revision.id:
                raise ValueError("theme revision_id does not match activated revision")
            self._themes.add(theme)
        for criterion in bundle.criteria:
            if criterion.revision_id != revision.id:
                raise ValueError(
                    "criterion revision_id does not match activated revision"
                )
            self._criteria.add(criterion)
        for exclusion in bundle.exclusions:
            if exclusion.revision_id != revision.id:
                raise ValueError(
                    "exclusion revision_id does not match activated revision"
                )
            self._exclusions.add(exclusion)

    def _supersede_active_revisions(
        self, search_strategy_id: str, *, keep_revision_id: str
    ) -> None:
        for revision in self._revisions.list_for_strategy(search_strategy_id):
            if revision.id == keep_revision_id:
                if revision.status is not RevisionStatus.ACTIVE:
                    self._revisions.update_status(revision.id, RevisionStatus.ACTIVE)
                continue
            if revision.status is RevisionStatus.ACTIVE:
                self._revisions.update_status(revision.id, RevisionStatus.SUPERSEDED)

    def _reactivate_revision(
        self, strategy: SearchStrategy, revision: SearchStrategyRevision
    ) -> None:
        if revision.search_strategy_id != strategy.id:
            raise ValueError("cannot reactivate revision owned by another strategy")
        snapshot = self._snapshots.load_snapshot(revision.id)
        if snapshot is None:
            raise ValueError(f"revision {revision.id} has no persisted content")
        self._supersede_active_revisions(strategy.id, keep_revision_id=revision.id)
        self._set_current_revision(strategy, revision.id)

    def _set_current_revision(
        self, strategy: SearchStrategy, revision_id: str
    ) -> None:
        revision = self._revisions.get_by_id(revision_id)
        if revision is None:
            raise ValueError(f"revision {revision_id} not found")
        if revision.search_strategy_id != strategy.id:
            raise ValueError("current_revision_id must reference the same strategy")
        updated = SearchStrategy(
            id=strategy.id,
            owner_key=strategy.owner_key,
            current_revision_id=revision_id,
            created_at=strategy.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self._strategies.save(updated)
