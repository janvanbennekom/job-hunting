"""Deterministic structured search strategy edits (no LLM)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from jobhunter.application.strategy_conversation.diff import build_strategy_diff
from jobhunter.application.strategy_conversation.dtos import (
    ProposalOutcome,
    StrategyChangeProposal,
)
from jobhunter.application.strategy_conversation.mutations import (
    MutationApplyError,
    apply_mutations,
)
from jobhunter.domain import RevisionChangeSource
from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
    StrategyRevisionSnapshotRepository,
)
from jobhunter.infrastructure.search_strategy.bundle_rebind import (
    finalize_bundle_for_strategy,
)
from jobhunter.infrastructure.search_strategy.identity import search_strategy_id


class StructuredStrategyEditService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._strategies = SearchStrategyRepository(session)
        self._snapshots = StrategyRevisionSnapshotRepository(session)

    def propose_mutations(
        self,
        mutations: list[dict[str, Any]],
        *,
        change_summary: str,
        owner_key: str = PRIMARY_PROFILE_KEY,
    ) -> StrategyChangeProposal:
        proposal_id = str(uuid.uuid4())
        strategy = self._strategies.get_by_owner_key(owner_key)
        if strategy is None or strategy.current_revision_id is None:
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id="",
                user_message="structured edit",
                outcome=ProposalOutcome.UNUSABLE,
                summary="No active search strategy revision is configured.",
                assumptions=[],
                clarification_questions=[],
                change_summary=change_summary,
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
                change_source=RevisionChangeSource.STRUCTURED_EDIT,
            )

        snapshot = self._snapshots.load_snapshot(strategy.current_revision_id)
        if snapshot is None:
            raise RuntimeError("current revision snapshot missing")

        current_bundle = RevisionContentBundle(
            themes=tuple(snapshot.themes),
            criteria=tuple(snapshot.criteria),
            exclusions=tuple(snapshot.exclusions),
        )
        try:
            mutated = apply_mutations(current_bundle, mutations)
        except MutationApplyError as exc:
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id=snapshot.revision.id,
                user_message="structured edit",
                outcome=ProposalOutcome.INVALID,
                summary="Structured edit could not be applied.",
                assumptions=[],
                clarification_questions=[],
                change_summary=change_summary,
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
                validation_errors=[str(exc)],
                change_source=RevisionChangeSource.STRUCTURED_EDIT,
            )

        sid = search_strategy_id(owner_key)
        rebound, content_hash = finalize_bundle_for_strategy(sid, mutated)
        if content_hash == snapshot.revision.content_hash:
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id=snapshot.revision.id,
                user_message="structured edit",
                outcome=ProposalOutcome.NO_OP,
                summary="No change; proposed content matches the active revision.",
                assumptions=[],
                clarification_questions=[],
                change_summary=change_summary,
                proposed_bundle=rebound,
                content_hash=content_hash,
                proposed_revision_id=rebound.themes[0].revision_id
                if rebound.themes
                else None,
                diff_lines=[],
                change_source=RevisionChangeSource.STRUCTURED_EDIT,
            )

        diff_lines = build_strategy_diff(current_bundle, rebound)
        return StrategyChangeProposal(
            proposal_id=proposal_id,
            base_revision_id=snapshot.revision.id,
            user_message="structured edit",
            outcome=ProposalOutcome.PROPOSED,
            summary="Structured edit ready for confirmation.",
            assumptions=[],
            clarification_questions=[],
            change_summary=change_summary or "Structured strategy edit",
            proposed_bundle=rebound,
            content_hash=content_hash,
            proposed_revision_id=rebound.themes[0].revision_id
            if rebound.themes
            else None,
            diff_lines=diff_lines,
            change_source=RevisionChangeSource.STRUCTURED_EDIT,
        )
