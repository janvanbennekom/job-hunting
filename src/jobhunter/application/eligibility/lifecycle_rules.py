"""Map Phase 5 lifecycle state to eligibility rule results."""

from __future__ import annotations

from jobhunter.domain.eligibility_enums import EligibilityRuleKind, RuleTriState
from jobhunter.domain.eligibility_rule_result import EligibilityRuleResult
from jobhunter.domain.enums import LifecycleStatus
from jobhunter.domain.opportunity import Opportunity


def evaluate_lifecycle_rules(
    opportunity: Opportunity, *, decision_id: str
) -> list[EligibilityRuleResult]:
    results: list[EligibilityRuleResult] = []
    if opportunity.lifecycle_status is LifecycleStatus.EXPIRED:
        results.append(
            EligibilityRuleResult(
                decision_id=decision_id,
                rule_kind=EligibilityRuleKind.LIFECYCLE,
                rule_code="deadline_passed",
                outcome=RuleTriState.FALSE,
                summary="Opportunity lifecycle is EXPIRED",
                evidence=opportunity.lifecycle_status.value,
            )
        )
    elif opportunity.lifecycle_status is LifecycleStatus.CLOSED:
        results.append(
            EligibilityRuleResult(
                decision_id=decision_id,
                rule_kind=EligibilityRuleKind.LIFECYCLE,
                rule_code="source_closed",
                outcome=RuleTriState.FALSE,
                summary="Opportunity lifecycle is CLOSED",
                evidence=opportunity.lifecycle_status.value,
            )
        )
    else:
        results.append(
            EligibilityRuleResult(
                decision_id=decision_id,
                rule_kind=EligibilityRuleKind.LIFECYCLE,
                rule_code="lifecycle_open",
                outcome=RuleTriState.TRUE,
                summary="Lifecycle does not block eligibility",
                evidence=opportunity.lifecycle_status.value,
            )
        )
    return results
