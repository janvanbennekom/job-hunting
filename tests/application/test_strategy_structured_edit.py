"""Structured strategy edit tests (Phase 15, no LLM)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.strategy_conversation import (
    StrategyChangeConfirmationService,
    StrategyQueryService,
)
from jobhunter.application.strategy_conversation.dtos import ProposalOutcome
from jobhunter.application.strategy_structured_edit.service import StructuredStrategyEditService
from jobhunter.domain import PreferenceStrength, RevisionChangeSource
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
    SearchStrategyRevisionRepository,
)
from tests.application.test_strategy_conversation import OWNER, _activate_owner

pytestmark = pytest.mark.integration


def test_structured_edit_proposes_and_activates_revision(db_session: Session) -> None:
    base_revision = _activate_owner(db_session)
    service = StructuredStrategyEditService(db_session)
    proposal = service.propose_mutations(
        [
            {
                "op": "SET_THEME_STRENGTH",
                "theme_key": "lis_implementation",
                "strength": PreferenceStrength.STRONGLY_PREFERRED.value,
            }
        ],
        change_summary="Increase LIS theme strength",
        owner_key=OWNER,
    )
    assert proposal.outcome is ProposalOutcome.PROPOSED
    assert proposal.change_source is RevisionChangeSource.STRUCTURED_EDIT
    assert proposal.diff_lines

    confirm = StrategyChangeConfirmationService(db_session).confirm(
        proposal, owner_key=OWNER
    )
    assert confirm.activated is not None
    assert confirm.activated.created_new_revision

    strategy = SearchStrategyRepository(db_session).get_by_owner_key(OWNER)
    assert strategy.current_revision_id != base_revision
    history = StrategyQueryService(db_session).list_revision_history(OWNER)
    latest = max(history, key=lambda row: row.revision_number)
    assert latest.change_source == RevisionChangeSource.STRUCTURED_EDIT.value


def test_structured_edit_no_op_same_content(db_session: Session) -> None:
    _activate_owner(db_session)
    service = StructuredStrategyEditService(db_session)
    proposal = service.propose_mutations(
        [
            {
                "op": "SET_THEME_STRENGTH",
                "theme_key": "lis_implementation",
                "strength": PreferenceStrength.PREFERRED.value,
            }
        ],
        change_summary="No actual change",
        owner_key=OWNER,
    )
    assert proposal.outcome is ProposalOutcome.NO_OP

    revisions = SearchStrategyRevisionRepository(db_session).list_for_strategy(
        SearchStrategyRepository(db_session).get_by_owner_key(OWNER).id
    )
    assert len(revisions) == 1
