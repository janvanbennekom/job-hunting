"""Unit tests for Phase 7 eligibility filtering."""

from __future__ import annotations

from datetime import date, datetime, timezone

from jobhunter.application.eligibility.aggregate import aggregate_eligibility_status
from jobhunter.application.eligibility.exclusion_rules import evaluate_exclusion
from jobhunter.application.eligibility.hard_constraint_rules import (
    evaluate_hard_constraint,
)
from jobhunter.application.eligibility.lifecycle_rules import evaluate_lifecycle_rules
from jobhunter.application.eligibility.service import EligibilityFilterService
from jobhunter.domain.eligibility_enums import RuleTriState
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus, OpportunityType
from jobhunter.domain.exclusion_criterion import ExclusionCriterion
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.search_strategy_revision import SearchStrategyRevision
from jobhunter.domain.strategy_criterion import StrategyCriterion
from jobhunter.domain.strategy_criterion_values import (
    EngagementModelConstraintValue,
    GeographyConstraintValue,
)
from jobhunter.domain.strategy_enums import (
    ExclusionCode,
    RevisionChangeSource,
    RevisionStatus,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.infrastructure.persistence.strategy_repositories import (
    PersistedRevisionSnapshot,
)


def _opp(**kwargs) -> Opportunity:
    defaults = {
        "title": "Senior GIS Specialist",
        "description": "Land administration systems implementation.",
        "lifecycle_status": LifecycleStatus.NEW,
    }
    defaults.update(kwargs)
    return Opportunity(**defaults)


def _snapshot(
    exclusions: list[ExclusionCriterion] | None = None,
    criteria: list[StrategyCriterion] | None = None,
) -> PersistedRevisionSnapshot:
    revision = SearchStrategyRevision(
        id="rev-test-001",
        search_strategy_id="strategy-test",
        revision_number=1,
        status=RevisionStatus.ACTIVE,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        change_summary="test",
        change_source=RevisionChangeSource.INITIAL_SEED,
        content_hash="a" * 64,
    )
    return PersistedRevisionSnapshot(
        revision=revision,
        themes=[],
        criteria=criteria or [],
        exclusions=exclusions or [],
    )


def test_expired_lifecycle_ineligible() -> None:
    opp = _opp(lifecycle_status=LifecycleStatus.EXPIRED)
    rules = evaluate_lifecycle_rules(opp, decision_id="d1")
    assert aggregate_eligibility_status(rules) is EligibilityStatus.INELIGIBLE


def test_closed_lifecycle_ineligible() -> None:
    opp = _opp(lifecycle_status=LifecycleStatus.CLOSED)
    rules = evaluate_lifecycle_rules(opp, decision_id="d1")
    assert aggregate_eligibility_status(rules) is EligibilityStatus.INELIGIBLE


def test_internship_exclusion_high_confidence() -> None:
    opp = _opp(title="Call for Expression of Interest – Internship Programme")
    ex = ExclusionCriterion(
        revision_id="rev-test-001",
        exclusion_code=ExclusionCode.JUNIOR_OR_INTERNSHIP,
    )
    rule = evaluate_exclusion(opp, ex, decision_id="d1")
    assert rule.outcome is RuleTriState.FALSE


def test_volunteer_exclusion_strong_phrase() -> None:
    opp = _opp(description="This is an unpaid volunteer assignment in Rome.")
    ex = ExclusionCriterion(
        revision_id="rev-test-001",
        exclusion_code=ExclusionCode.VOLUNTEER,
    )
    rule = evaluate_exclusion(opp, ex, decision_id="d1")
    assert rule.outcome is RuleTriState.FALSE


def test_national_only_clear_phrase() -> None:
    opp = _opp(description="National consultant only. Must be citizen.")
    ex = ExclusionCriterion(
        revision_id="rev-test-001",
        exclusion_code=ExclusionCode.NATIONAL_CONSULTANT_ONLY,
    )
    rule = evaluate_exclusion(opp, ex, decision_id="d1")
    assert rule.outcome is RuleTriState.FALSE


def test_national_only_ambiguous_review() -> None:
    opp = _opp(description="National consultant experience preferred.")
    ex = ExclusionCriterion(
        revision_id="rev-test-001",
        exclusion_code=ExclusionCode.NATIONAL_CONSULTANT_ONLY,
    )
    rule = evaluate_exclusion(opp, ex, decision_id="d1")
    assert rule.outcome is RuleTriState.UNKNOWN
    assert rule.suggests_review is True


def test_missing_information_unknown_not_ineligible() -> None:
    opp = _opp(description="Land administration consultant for FAO.")
    ex = ExclusionCriterion(
        revision_id="rev-test-001",
        exclusion_code=ExclusionCode.NATIONAL_CONSULTANT_ONLY,
    )
    rule = evaluate_exclusion(opp, ex, decision_id="d1")
    assert rule.outcome is RuleTriState.TRUE
    snapshot = _snapshot(exclusions=[ex])
    result = EligibilityFilterService.__new__(EligibilityFilterService)
    evaluation = EligibilityFilterService.evaluate(result, opp, snapshot)
    assert evaluation.decision.status is EligibilityStatus.ELIGIBLE


def test_all_rules_pass_eligible() -> None:
    opp = _opp()
    snapshot = _snapshot(
        exclusions=[
            ExclusionCriterion(
                revision_id="rev-test-001",
                exclusion_code=ExclusionCode.JUNIOR_OR_INTERNSHIP,
            )
        ]
    )
    service = EligibilityFilterService.__new__(EligibilityFilterService)
    evaluation = EligibilityFilterService.evaluate(service, opp, snapshot)
    assert evaluation.decision.status is EligibilityStatus.ELIGIBLE


def test_hard_constraint_geography_fail() -> None:
    opp = _opp(location="Kenya-Nairobi")
    criterion = StrategyCriterion(
        revision_id="rev-test-001",
        category=StrategyCriterionCategory.HARD_CONSTRAINT,
        code=StrategyParameterCode.GEOGRAPHY,
        value=GeographyConstraintValue(excluded_countries=("Kenya",)),
    )
    rule = evaluate_hard_constraint(opp, criterion, decision_id="d1")
    assert rule.outcome is RuleTriState.FALSE


def test_hard_constraint_geography_pass() -> None:
    opp = _opp(location="Italy-Rome")
    criterion = StrategyCriterion(
        revision_id="rev-test-001",
        category=StrategyCriterionCategory.HARD_CONSTRAINT,
        code=StrategyParameterCode.GEOGRAPHY,
        value=GeographyConstraintValue(excluded_countries=("Kenya",)),
    )
    rule = evaluate_hard_constraint(opp, criterion, decision_id="d1")
    assert rule.outcome is RuleTriState.TRUE


def test_hard_constraint_engagement_unknown_sparse_data() -> None:
    opp = _opp(description="Land administration consultant.")
    criterion = StrategyCriterion(
        revision_id="rev-test-001",
        category=StrategyCriterionCategory.HARD_CONSTRAINT,
        code=StrategyParameterCode.ENGAGEMENT_MODEL,
        value=EngagementModelConstraintValue(single_consultant_only=True),
    )
    rule = evaluate_hard_constraint(opp, criterion, decision_id="d1")
    assert rule.outcome is RuleTriState.UNKNOWN


def test_fao_sparse_text_no_false_ineligible() -> None:
    opp = _opp(
        title="Monitoring Evaluation Accountability Learning (MEAL) Specialist",
        description=(
            "Title: Monitoring Evaluation Accountability Learning (MEAL) Specialist\n"
            "Opportunity category: Non-staff opportunities\n"
            "Job field: NPP (National Project Personnel)\n"
            "Locations: India-New Delhi"
        ),
        location="India-New Delhi",
    )
    snapshot = _snapshot(
        exclusions=[
            ExclusionCriterion(
                revision_id="rev-test-001",
                exclusion_code=ExclusionCode.REQUIRES_MULTI_PERSON_TEAM_OR_CONSORTIUM,
            ),
            ExclusionCriterion(
                revision_id="rev-test-001",
                exclusion_code=ExclusionCode.NATIONAL_CONSULTANT_ONLY,
            ),
        ]
    )
    service = EligibilityFilterService.__new__(EligibilityFilterService)
    evaluation = EligibilityFilterService.evaluate(service, opp, snapshot)
    assert evaluation.decision.status is not EligibilityStatus.INELIGIBLE


def test_revision_id_on_decision() -> None:
    snapshot = _snapshot()
    service = EligibilityFilterService.__new__(EligibilityFilterService)
    evaluation = EligibilityFilterService.evaluate(service, _opp(), snapshot)
    assert evaluation.decision.search_strategy_revision_id == "rev-test-001"
