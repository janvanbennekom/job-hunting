"""Aggregate rule outcomes into EligibilityStatus."""

from __future__ import annotations

from jobhunter.domain.eligibility_enums import RuleTriState
from jobhunter.domain.eligibility_rule_result import EligibilityRuleResult
from jobhunter.domain.enums import EligibilityStatus


def aggregate_eligibility_status(
    rule_results: list[EligibilityRuleResult],
) -> EligibilityStatus:
    if any(
        result.outcome is RuleTriState.FALSE for result in rule_results
    ):
        return EligibilityStatus.INELIGIBLE
    if any(result.suggests_review for result in rule_results):
        return EligibilityStatus.REVIEW_REQUIRED
    if any(
        result.outcome is RuleTriState.UNKNOWN for result in rule_results
    ):
        return EligibilityStatus.UNKNOWN
    return EligibilityStatus.ELIGIBLE
