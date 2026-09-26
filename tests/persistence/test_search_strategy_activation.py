"""Integration tests for search strategy activation (Phase 4A.3)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from jobhunter.domain import (
    ExclusionCode,
    ExclusionCriterion,
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
    StrategyRevisionSnapshotRepository,
)
from jobhunter.infrastructure.search_strategy.activation_service import (
    SearchStrategyActivationService,
)
from jobhunter.infrastructure.search_strategy.identity import (
    exclusion_criterion_id,
    strategy_criterion_id,
    theme_id,
)

pytestmark = pytest.mark.integration

OWNER = "activation-test-owner"


def _bundle(revision_id: str) -> RevisionContentBundle:
    return RevisionContentBundle(
        themes=(
            SearchTheme(
                id=theme_id(revision_id, "lis"),
                revision_id=revision_id,
                theme_key="lis",
                label="LIS",
                strength=PreferenceStrength.PREFERRED,
            ),
        ),
        criteria=(
            StrategyCriterion(
                id=strategy_criterion_id(
                    revision_id,
                    StrategyCriterionCategory.PREFERENCE.value,
                    StrategyParameterCode.TRAVEL_PATTERN.value,
                ),
                revision_id=revision_id,
                category=StrategyCriterionCategory.PREFERENCE,
                code=StrategyParameterCode.TRAVEL_PATTERN,
                value=parse_criterion_value(
                    StrategyCriterionCategory.PREFERENCE,
                    StrategyParameterCode.TRAVEL_PATTERN,
                    {"aspect": "continuous_abroad"},
                ),
                strength=PreferenceStrength.LESS_PREFERRED,
            ),
        ),
        exclusions=(
            ExclusionCriterion(
                id=exclusion_criterion_id(revision_id, ExclusionCode.VOLUNTEER.value),
                revision_id=revision_id,
                exclusion_code=ExclusionCode.VOLUNTEER,
            ),
        ),
    )


def test_activation_creates_strategy_and_revision(db_session: Session) -> None:
    service = SearchStrategyActivationService(db_session)
    # ids assigned inside activation path via content hash — use placeholder then service rebinds
    from jobhunter.domain.strategy_content_hash import compute_revision_content_hash
    from jobhunter.infrastructure.search_strategy.identity import (
        revision_id_for_content,
        search_strategy_id,
    )

    strategy_id = search_strategy_id(OWNER)
    placeholder = "pending"
    bundle = _bundle(placeholder)
    content_hash = compute_revision_content_hash(bundle)
    revision_id = revision_id_for_content(strategy_id, content_hash)
    bundle = _bundle(revision_id)

    result = service.activate(
        OWNER,
        bundle,
        change_summary="First",
        change_source=RevisionChangeSource.MANUAL,
        apply=True,
    )
    assert result.created_new_revision
    assert not result.no_op

    strategy = SearchStrategyRepository(db_session).get_by_owner_key(OWNER)
    assert strategy is not None
    assert strategy.current_revision_id == result.revision_id

    revisions = SearchStrategyRevisionRepository(db_session).list_for_strategy(
        strategy.id
    )
    assert len(revisions) == 1
    assert revisions[0].status is RevisionStatus.ACTIVE

    snapshot = StrategyRevisionSnapshotRepository(db_session).load_snapshot(
        result.revision_id
    )
    assert snapshot is not None
    assert len(snapshot.themes) == 1


def test_activation_no_op_when_content_unchanged(db_session: Session) -> None:
    service = SearchStrategyActivationService(db_session)
    from jobhunter.domain.strategy_content_hash import compute_revision_content_hash
    from jobhunter.infrastructure.search_strategy.identity import (
        revision_id_for_content,
        search_strategy_id,
    )

    strategy_id = search_strategy_id(OWNER)
    revision_id = revision_id_for_content(
        strategy_id, compute_revision_content_hash(_bundle("pending"))
    )
    bundle = _bundle(revision_id)
    service.activate(
        OWNER,
        bundle,
        change_summary="First",
        change_source=RevisionChangeSource.MANUAL,
        apply=True,
    )
    second = service.activate(
        OWNER,
        bundle,
        change_summary="Repeat",
        change_source=RevisionChangeSource.MANUAL,
        apply=True,
    )
    assert second.no_op
    revisions = SearchStrategyRevisionRepository(db_session).list_for_strategy(
        strategy_id
    )
    assert len(revisions) == 1
