"""Integration: structured criterion edit creates revision."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.strategy_conversation import StrategyChangeConfirmationService
from jobhunter.application.strategy_conversation.dtos import ProposalOutcome
from jobhunter.application.strategy_structured_edit.service import StructuredStrategyEditService
from jobhunter.domain import PreferenceStrength, RevisionChangeSource
from tests.application.test_strategy_conversation import OWNER, _activate_owner

pytestmark = pytest.mark.integration


def test_structured_criterion_edit(db_session: Session) -> None:
    _activate_owner(db_session)
    proposal = StructuredStrategyEditService(db_session).propose_mutations(
        [
            {
                "op": "SET_CRITERION",
                "category": "PREFERENCE",
                "code": "ASSIGNMENT_DELIVERY_MODE",
                "value": {
                    "implementation": PreferenceStrength.STRONGLY_PREFERRED.value,
                    "advisory": PreferenceStrength.ACCEPTABLE.value,
                },
            }
        ],
        change_summary="Prefer implementation delivery",
        owner_key=OWNER,
    )
    assert proposal.outcome is ProposalOutcome.PROPOSED
    assert proposal.change_source is RevisionChangeSource.STRUCTURED_EDIT
    confirm = StrategyChangeConfirmationService(db_session).confirm(
        proposal, owner_key=OWNER
    )
    assert confirm.activated is not None
    assert confirm.activated.created_new_revision
