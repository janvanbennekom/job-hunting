"""Mappers for eligibility persistence."""

from __future__ import annotations

from jobhunter.domain.eligibility_decision import EligibilityDecision
from jobhunter.domain.eligibility_enums import EligibilityRuleKind, RuleTriState
from jobhunter.domain.eligibility_rule_result import EligibilityRuleResult
from jobhunter.domain.enums import EligibilityStatus
from jobhunter.infrastructure.persistence.models import (
    EligibilityDecisionRow,
    EligibilityRuleResultRow,
)


def eligibility_decision_to_row(entity: EligibilityDecision) -> EligibilityDecisionRow:
    return EligibilityDecisionRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        search_strategy_revision_id=entity.search_strategy_revision_id,
        evaluated_at=entity.evaluated_at,
        status=entity.status.value,
    )


def eligibility_decision_to_domain(row: EligibilityDecisionRow) -> EligibilityDecision:
    return EligibilityDecision(
        id=row.id,
        opportunity_id=row.opportunity_id,
        search_strategy_revision_id=row.search_strategy_revision_id,
        evaluated_at=row.evaluated_at,
        status=EligibilityStatus(row.status),
    )


def eligibility_rule_result_to_row(
    entity: EligibilityRuleResult,
) -> EligibilityRuleResultRow:
    return EligibilityRuleResultRow(
        id=entity.id,
        decision_id=entity.decision_id,
        rule_kind=entity.rule_kind.value,
        rule_code=entity.rule_code,
        outcome=entity.outcome.value,
        suggests_review=entity.suggests_review,
        summary=entity.summary,
        evidence=entity.evidence,
    )


def eligibility_rule_result_to_domain(
    row: EligibilityRuleResultRow,
) -> EligibilityRuleResult:
    return EligibilityRuleResult(
        id=row.id,
        decision_id=row.decision_id,
        rule_kind=EligibilityRuleKind(row.rule_kind),
        rule_code=row.rule_code,
        outcome=RuleTriState(row.outcome),
        suggests_review=row.suggests_review,
        summary=row.summary,
        evidence=row.evidence,
    )
