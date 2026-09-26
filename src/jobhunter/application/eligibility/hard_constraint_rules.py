"""Deterministic evaluation of HARD_CONSTRAINT StrategyCriterion rules."""

from __future__ import annotations

import re

from jobhunter.application.eligibility.opportunity_text import opportunity_text_corpus
from jobhunter.domain.eligibility_enums import EligibilityRuleKind, RuleTriState
from jobhunter.domain.eligibility_rule_result import EligibilityRuleResult
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.strategy_criterion import StrategyCriterion
from jobhunter.domain.strategy_criterion_values import (
    AssignmentDurationConstraintValue,
    EngagementModelConstraintValue,
    GeographyConstraintValue,
)
from jobhunter.domain.strategy_enums import StrategyCriterionCategory, StrategyParameterCode


def _result(
    decision_id: str,
    code: StrategyParameterCode,
    outcome: RuleTriState,
    *,
    suggests_review: bool = False,
    summary: str | None = None,
    evidence: str | None = None,
) -> EligibilityRuleResult:
    return EligibilityRuleResult(
        decision_id=decision_id,
        rule_kind=EligibilityRuleKind.HARD_CONSTRAINT,
        rule_code=code.value,
        outcome=outcome,
        suggests_review=suggests_review,
        summary=summary,
        evidence=evidence,
    )


def evaluate_hard_constraint(
    opportunity: Opportunity,
    criterion: StrategyCriterion,
    *,
    decision_id: str,
) -> EligibilityRuleResult:
    if criterion.category is not StrategyCriterionCategory.HARD_CONSTRAINT:
        raise ValueError("Expected HARD_CONSTRAINT criterion")
    if not criterion.is_active:
        return _result(
            decision_id,
            criterion.code,
            RuleTriState.TRUE,
            summary="Hard constraint inactive; skipped",
        )

    code = criterion.code
    value = criterion.value
    corpus = opportunity_text_corpus(opportunity)
    location = (opportunity.location or "").lower()

    if code is StrategyParameterCode.GEOGRAPHY:
        if not isinstance(value, GeographyConstraintValue):
            return _result(
                decision_id,
                code,
                RuleTriState.UNKNOWN,
                summary="Unexpected geography constraint value type",
            )
        for country in value.excluded_countries:
            needle = country.lower()
            if needle in corpus or needle in location:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.FALSE,
                    summary="Opportunity location matches excluded country",
                    evidence=country,
                )
        return _result(
            decision_id,
            code,
            RuleTriState.TRUE,
            summary="No excluded geography matched",
        )

    if code is StrategyParameterCode.ENGAGEMENT_MODEL:
        if not isinstance(value, EngagementModelConstraintValue):
            return _result(
                decision_id,
                code,
                RuleTriState.UNKNOWN,
                summary="Unexpected engagement constraint value type",
            )
        if not value.single_consultant_only:
            return _result(
                decision_id,
                code,
                RuleTriState.TRUE,
                summary="Constraint does not require single consultant",
            )
        strong = [
            r"\bconsortium required\b",
            r"\bmulti[- ]person team\b",
            r"\bteam of consultants\b",
        ]
        for pattern in strong:
            match = re.search(pattern, corpus)
            if match:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.FALSE,
                    summary="Violates single-consultant hard constraint",
                    evidence=match.group(0),
                )
        return _result(
            decision_id,
            code,
            RuleTriState.UNKNOWN,
            summary="Insufficient evidence to confirm single-consultant engagement",
        )

    if code is StrategyParameterCode.ASSIGNMENT_DURATION:
        if not isinstance(value, AssignmentDurationConstraintValue):
            return _result(
                decision_id,
                code,
                RuleTriState.UNKNOWN,
                summary="Unexpected duration constraint value type",
            )
        return _result(
            decision_id,
            code,
            RuleTriState.UNKNOWN,
            summary="Opportunity duration not available for deterministic check",
        )

    return _result(
        decision_id,
        code,
        RuleTriState.UNKNOWN,
        summary="Hard constraint code not supported for deterministic evaluation",
    )
