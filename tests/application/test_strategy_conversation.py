"""Phase 11 conversational strategy tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from jobhunter.ai.fake_strategy_model import FakeStrategyChangeModel
from jobhunter.ai.strategy_factory import StrategyProvider, resolve_strategy_change_model
from jobhunter.application.strategy_conversation import (
    StrategyChangeConfirmationService,
    StrategyConversationService,
    StrategyQueryService,
)
from jobhunter.application.strategy_conversation.dtos import ProposalOutcome
from jobhunter.domain import (
    PreferenceStrength,
    RevisionChangeSource,
    RevisionStatus,
    SearchTheme,
    StrategyCriterion,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.domain.strategy_criterion_values import parse_criterion_value
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
    SearchStrategyRevisionRepository,
)
from jobhunter.infrastructure.search_strategy.activation_service import (
    SearchStrategyActivationService,
)
from jobhunter.infrastructure.search_strategy.identity import (
    strategy_criterion_id,
    theme_id,
)

pytestmark = pytest.mark.integration

OWNER = "strategy-conversation-test-owner"


def _seed_bundle(revision_id: str) -> RevisionContentBundle:
    return RevisionContentBundle(
        themes=(
            SearchTheme(
                id=theme_id(revision_id, "lis_implementation"),
                revision_id=revision_id,
                theme_key="lis_implementation",
                label="LIS",
                strength=PreferenceStrength.PREFERRED,
            ),
            SearchTheme(
                id=theme_id(revision_id, "system_integration"),
                revision_id=revision_id,
                theme_key="system_integration",
                label="Integration",
                strength=PreferenceStrength.ACCEPTABLE,
            ),
        ),
        criteria=(
            StrategyCriterion(
                id=strategy_criterion_id(
                    revision_id,
                    StrategyCriterionCategory.PREFERENCE.value,
                    StrategyParameterCode.ASSIGNMENT_DELIVERY_MODE.value,
                ),
                revision_id=revision_id,
                category=StrategyCriterionCategory.PREFERENCE,
                code=StrategyParameterCode.ASSIGNMENT_DELIVERY_MODE,
                value=parse_criterion_value(
                    StrategyCriterionCategory.PREFERENCE,
                    StrategyParameterCode.ASSIGNMENT_DELIVERY_MODE,
                    {"implementation": "PREFERRED", "advisory": "ACCEPTABLE"},
                ),
            ),
            StrategyCriterion(
                id=strategy_criterion_id(
                    revision_id,
                    StrategyCriterionCategory.PREFERENCE.value,
                    StrategyParameterCode.GEOGRAPHY.value,
                ),
                revision_id=revision_id,
                category=StrategyCriterionCategory.PREFERENCE,
                code=StrategyParameterCode.GEOGRAPHY,
                value=parse_criterion_value(
                    StrategyCriterionCategory.PREFERENCE,
                    StrategyParameterCode.GEOGRAPHY,
                    {"regions": [], "countries": []},
                ),
            ),
        ),
        exclusions=(),
    )


def _activate_owner(session: Session) -> str:
    service = SearchStrategyActivationService(session)
    bundle = _seed_bundle("pending")
    from jobhunter.infrastructure.search_strategy.bundle_rebind import (
        finalize_bundle_for_strategy,
    )
    from jobhunter.infrastructure.search_strategy.identity import search_strategy_id

    rebound, _ = finalize_bundle_for_strategy(search_strategy_id(OWNER), bundle)
    result = service.activate(
        OWNER,
        rebound,
        change_summary="Test seed",
        change_source=RevisionChangeSource.INITIAL_SEED,
        apply=True,
    )
    assert result.revision_id is not None
    return result.revision_id


def test_fake_proposal_and_confirm_new_revision(db_session: Session) -> None:
    base_revision = _activate_owner(db_session)
    model = FakeStrategyChangeModel()
    message = (
        "Focus on hands-on implementation and LIS implementation and system integration"
    )
    proposal = StrategyConversationService(db_session).propose(
        message, model, owner_key=OWNER
    )
    assert proposal.outcome is ProposalOutcome.PROPOSED
    assert proposal.diff_lines
    assert proposal.proposed_bundle is not None

    confirm = StrategyChangeConfirmationService(db_session).confirm(
        proposal, owner_key=OWNER
    )
    assert confirm.activated is not None
    assert confirm.activated.created_new_revision

    strategy = SearchStrategyRepository(db_session).get_by_owner_key(OWNER)
    assert strategy is not None
    assert strategy.current_revision_id != base_revision

    revisions = SearchStrategyRevisionRepository(db_session).list_for_strategy(
        strategy.id
    )
    assert len(revisions) == 2
    old = next(r for r in revisions if r.id == base_revision)
    assert old.status is RevisionStatus.SUPERSEDED


def test_cancel_leaves_revision_unchanged(db_session: Session) -> None:
    base_revision = _activate_owner(db_session)
    proposal = StrategyConversationService(db_session).propose(
        "hands-on implementation and LIS implementation",
        FakeStrategyChangeModel(),
        owner_key=OWNER,
    )
    StrategyChangeConfirmationService(db_session).cancel(proposal)
    strategy = SearchStrategyRepository(db_session).get_by_owner_key(OWNER)
    assert strategy.current_revision_id == base_revision


def test_needs_clarification(db_session: Session) -> None:
    _activate_owner(db_session)
    proposal = StrategyConversationService(db_session).propose(
        "maybe something clarify",
        FakeStrategyChangeModel(),
        owner_key=OWNER,
    )
    assert proposal.outcome is ProposalOutcome.NEEDS_CLARIFICATION
    assert proposal.clarification_questions


def test_invalid_mutation_payload(db_session: Session) -> None:
    _activate_owner(db_session)
    model = FakeStrategyChangeModel(
        fixed_payload={
            "outcome": "PROPOSED",
            "summary": "bad",
            "assumptions": [],
            "clarification_questions": [],
            "change_summary": "bad",
            "mutations": [{"op": "SET_THEME_STRENGTH", "theme_key": "missing"}],
        }
    )
    proposal = StrategyConversationService(db_session).propose(
        "test", model, owner_key=OWNER
    )
    assert proposal.outcome is ProposalOutcome.INVALID


def test_query_read_only_does_not_change_revision(db_session: Session) -> None:
    base_revision = _activate_owner(db_session)
    StrategyQueryService(db_session).get_active_view(OWNER)
    StrategyQueryService(db_session).list_revision_history(OWNER)
    strategy = SearchStrategyRepository(db_session).get_by_owner_key(OWNER)
    assert strategy.current_revision_id == base_revision


def test_openai_resolve_fails_without_config() -> None:
    from jobhunter.infrastructure.config import Settings

    settings = Settings.from_environ({})
    with pytest.raises(RuntimeError):
        resolve_strategy_change_model(settings, StrategyProvider.OPENAI)


def test_fake_provider_explicit() -> None:
    from jobhunter.infrastructure.config import Settings

    settings = Settings.from_environ({})
    model = resolve_strategy_change_model(settings, StrategyProvider.FAKE)
    assert model.provider == "fake"
