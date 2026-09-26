"""Confirm or reject conversational strategy proposals."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from jobhunter.application.strategy_conversation.dtos import (
    ProposalOutcome,
    StrategyChangeProposal,
)
from jobhunter.domain import RevisionChangeSource
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
)
from jobhunter.infrastructure.search_strategy.activation_service import (
    ActivationResult,
    SearchStrategyActivationService,
)


@dataclass(frozen=True, slots=True)
class ConfirmationResult:
    activated: ActivationResult | None
    rejected: bool
    message: str


class StrategyChangeConfirmationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._strategies = SearchStrategyRepository(session)
        self._activation = SearchStrategyActivationService(session)

    def cancel(self, proposal: StrategyChangeProposal) -> ConfirmationResult:
        return ConfirmationResult(
            activated=None,
            rejected=True,
            message="Proposal cancelled; active strategy unchanged.",
        )

    def confirm(
        self,
        proposal: StrategyChangeProposal,
        *,
        owner_key: str = PRIMARY_PROFILE_KEY,
    ) -> ConfirmationResult:
        if proposal.outcome is not ProposalOutcome.PROPOSED:
            return ConfirmationResult(
                activated=None,
                rejected=True,
                message=f"Cannot confirm proposal with outcome {proposal.outcome.value}.",
            )
        if proposal.proposed_bundle is None:
            return ConfirmationResult(
                activated=None,
                rejected=True,
                message="Proposal has no bundle to activate.",
            )

        strategy = self._strategies.get_by_owner_key(owner_key)
        if strategy is None or strategy.current_revision_id != proposal.base_revision_id:
            return ConfirmationResult(
                activated=None,
                rejected=True,
                message=(
                    "Active strategy changed since the proposal was generated. "
                    "Generate a new proposal."
                ),
            )

        result = self._activation.activate(
            owner_key,
            proposal.proposed_bundle,
            change_summary=proposal.change_summary,
            change_source=RevisionChangeSource.CONVERSATION_CONFIRMED,
            apply=True,
        )
        if result.no_op:
            return ConfirmationResult(
                activated=result,
                rejected=False,
                message="No change required; content already active.",
            )
        return ConfirmationResult(
            activated=result,
            rejected=False,
            message="New search strategy revision activated.",
        )
