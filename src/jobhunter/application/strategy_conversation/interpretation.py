"""Propose search strategy changes from natural language."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from jobhunter.ai.strategy_protocol import StrategyChangeModel
from jobhunter.application.strategy_conversation.context import (
    snapshot_to_interpretation_context,
)
from jobhunter.application.strategy_conversation.diff import build_strategy_diff
from jobhunter.application.strategy_conversation.dtos import (
    ProposalOutcome,
    StrategyChangeProposal,
)
from jobhunter.application.strategy_conversation.mutations import (
    MutationApplyError,
    apply_mutations,
)
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


class StrategyConversationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._strategies = SearchStrategyRepository(session)
        self._snapshots = StrategyRevisionSnapshotRepository(session)

    def propose(
        self,
        user_message: str,
        model: StrategyChangeModel,
        *,
        owner_key: str = PRIMARY_PROFILE_KEY,
    ) -> StrategyChangeProposal:
        proposal_id = str(uuid.uuid4())
        message = user_message.strip()
        if not message:
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id="",
                user_message=user_message,
                outcome=ProposalOutcome.UNUSABLE,
                summary="Instruction is empty.",
                assumptions=[],
                clarification_questions=[],
                change_summary="",
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
            )

        strategy = self._strategies.get_by_owner_key(owner_key)
        if strategy is None or strategy.current_revision_id is None:
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id="",
                user_message=message,
                outcome=ProposalOutcome.UNUSABLE,
                summary="No active search strategy revision is configured.",
                assumptions=[],
                clarification_questions=[],
                change_summary="",
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
            )

        snapshot = self._snapshots.load_snapshot(strategy.current_revision_id)
        if snapshot is None:
            raise RuntimeError("current revision snapshot missing")

        context = snapshot_to_interpretation_context(snapshot)
        from jobhunter.ai.strategy_protocol import StrategyInterpretationRequest

        response = model.interpret(
            StrategyInterpretationRequest(
                user_message=message,
                current_strategy=context,
                owner_key=owner_key,
            )
        )
        if response.error:
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id=snapshot.revision.id,
                user_message=message,
                outcome=ProposalOutcome.UNUSABLE,
                summary="AI provider failed to interpret the request.",
                assumptions=[],
                clarification_questions=[],
                change_summary="",
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
                model_provider=response.provider,
                model_name=response.model_name,
                provider_error=response.error,
            )

        parsed = response.parsed or {}
        outcome_raw = str(parsed.get("outcome", "UNUSABLE"))
        summary = str(parsed.get("summary", ""))
        assumptions = [str(item) for item in parsed.get("assumptions") or []]
        questions = [
            str(item) for item in parsed.get("clarification_questions") or []
        ]
        change_summary = str(parsed.get("change_summary", "")).strip()

        if outcome_raw == "NEEDS_CLARIFICATION":
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id=snapshot.revision.id,
                user_message=message,
                outcome=ProposalOutcome.NEEDS_CLARIFICATION,
                summary=summary or "Clarification required before applying changes.",
                assumptions=assumptions,
                clarification_questions=questions,
                change_summary=change_summary,
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
                model_provider=response.provider,
                model_name=response.model_name,
            )

        if outcome_raw != "PROPOSED":
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id=snapshot.revision.id,
                user_message=message,
                outcome=ProposalOutcome.UNUSABLE,
                summary=summary or "Could not interpret the request.",
                assumptions=assumptions,
                clarification_questions=questions,
                change_summary=change_summary,
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
                model_provider=response.provider,
                model_name=response.model_name,
            )

        mutations = parsed.get("mutations")
        if not isinstance(mutations, list) or not mutations:
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id=snapshot.revision.id,
                user_message=message,
                outcome=ProposalOutcome.UNUSABLE,
                summary="No structured mutations were proposed.",
                assumptions=assumptions,
                clarification_questions=questions,
                change_summary=change_summary,
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
                model_provider=response.provider,
                model_name=response.model_name,
            )

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
                user_message=message,
                outcome=ProposalOutcome.INVALID,
                summary=summary,
                assumptions=assumptions,
                clarification_questions=questions,
                change_summary=change_summary or message[:120],
                proposed_bundle=None,
                content_hash=None,
                proposed_revision_id=None,
                validation_errors=[str(exc)],
                model_provider=response.provider,
                model_name=response.model_name,
            )

        strategy_id = search_strategy_id(owner_key)
        rebound, content_hash = finalize_bundle_for_strategy(strategy_id, mutated)
        if content_hash == snapshot.revision.content_hash:
            return StrategyChangeProposal(
                proposal_id=proposal_id,
                base_revision_id=snapshot.revision.id,
                user_message=message,
                outcome=ProposalOutcome.NO_OP,
                summary="Proposed changes match the current active strategy.",
                assumptions=assumptions,
                clarification_questions=[],
                change_summary=change_summary,
                proposed_bundle=rebound,
                content_hash=content_hash,
                proposed_revision_id=rebound.themes[0].revision_id
                if rebound.themes
                else None,
                diff_lines=[],
                model_provider=response.provider,
                model_name=response.model_name,
            )

        diff_lines = build_strategy_diff(current_bundle, rebound)
        if not change_summary:
            change_summary = f"Conversational update: {message[:120]}"

        return StrategyChangeProposal(
            proposal_id=proposal_id,
            base_revision_id=snapshot.revision.id,
            user_message=message,
            outcome=ProposalOutcome.PROPOSED,
            summary=summary,
            assumptions=assumptions,
            clarification_questions=questions,
            change_summary=change_summary,
            proposed_bundle=rebound,
            content_hash=content_hash,
            proposed_revision_id=rebound.themes[0].revision_id
            if rebound.themes
            else None,
            diff_lines=diff_lines,
            model_provider=response.provider,
            model_name=response.model_name,
        )
