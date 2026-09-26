"""Source-independent eligibility filtering service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.application.eligibility.aggregate import aggregate_eligibility_status
from jobhunter.application.eligibility.exclusion_rules import evaluate_exclusion
from jobhunter.application.eligibility.hard_constraint_rules import (
    evaluate_hard_constraint,
)
from jobhunter.application.eligibility.lifecycle_rules import evaluate_lifecycle_rules
from jobhunter.domain.eligibility_decision import EligibilityDecision
from jobhunter.domain.eligibility_rule_result import EligibilityRuleResult
from jobhunter.domain.enums import EligibilityStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.strategy_enums import StrategyCriterionCategory
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.eligibility_repositories import (
    EligibilityDecisionRepository,
    EligibilityRuleResultRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.infrastructure.persistence.strategy_repositories import (
    PersistedRevisionSnapshot,
    SearchStrategyRepository,
    StrategyRevisionSnapshotRepository,
)


@dataclass(slots=True)
class EligibilityEvaluationResult:
    decision: EligibilityDecision
    rule_results: list[EligibilityRuleResult]
    opportunity: Opportunity


class EligibilityFilterService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._opportunities = OpportunityRepository(session)
        self._decisions = EligibilityDecisionRepository(session)
        self._rule_results = EligibilityRuleResultRepository(session)
        self._strategies = SearchStrategyRepository(session)
        self._snapshots = StrategyRevisionSnapshotRepository(session)

    def resolve_active_snapshot(
        self, owner_key: str = PRIMARY_PROFILE_KEY
    ) -> PersistedRevisionSnapshot:
        strategy = self._strategies.get_by_owner_key(owner_key)
        if strategy is None or strategy.current_revision_id is None:
            raise RuntimeError(
                f"No active search strategy revision for owner {owner_key!r}"
            )
        snapshot = self._snapshots.load_snapshot(strategy.current_revision_id)
        if snapshot is None:
            raise RuntimeError(
                f"Search strategy revision {strategy.current_revision_id} not found"
            )
        return snapshot

    def evaluate(
        self,
        opportunity: Opportunity,
        snapshot: PersistedRevisionSnapshot,
        *,
        evaluated_at: datetime | None = None,
    ) -> EligibilityEvaluationResult:
        when = evaluated_at or datetime.now(timezone.utc)
        decision = EligibilityDecision(
            opportunity_id=opportunity.id,
            search_strategy_revision_id=snapshot.revision.id,
            evaluated_at=when,
            status=EligibilityStatus.UNKNOWN,
        )
        rule_results: list[EligibilityRuleResult] = []
        rule_results.extend(
            evaluate_lifecycle_rules(opportunity, decision_id=decision.id)
        )
        for exclusion in snapshot.exclusions:
            rule_results.append(
                evaluate_exclusion(
                    opportunity, exclusion, decision_id=decision.id
                )
            )
        for criterion in snapshot.criteria:
            if criterion.category is StrategyCriterionCategory.HARD_CONSTRAINT:
                rule_results.append(
                    evaluate_hard_constraint(
                        opportunity, criterion, decision_id=decision.id
                    )
                )

        decision.status = aggregate_eligibility_status(rule_results)
        return EligibilityEvaluationResult(
            decision=decision,
            rule_results=rule_results,
            opportunity=opportunity,
        )

    def evaluate_and_persist(
        self,
        opportunity_id: str,
        *,
        owner_key: str = PRIMARY_PROFILE_KEY,
        revision_id: str | None = None,
        evaluated_at: datetime | None = None,
    ) -> EligibilityEvaluationResult:
        opportunity = self._opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        if revision_id is not None:
            snapshot = self._snapshots.load_snapshot(revision_id)
            if snapshot is None:
                raise ValueError(f"Revision {revision_id} not found")
        else:
            snapshot = self.resolve_active_snapshot(owner_key)

        result = self.evaluate(
            opportunity, snapshot, evaluated_at=evaluated_at
        )
        saved_decision = self._decisions.save(result.decision)
        saved_rules = [
            self._rule_results.save(rule) for rule in result.rule_results
        ]
        updated = Opportunity(
            id=opportunity.id,
            title=opportunity.title,
            organisation=opportunity.organisation,
            location=opportunity.location,
            description=opportunity.description,
            publication_date=opportunity.publication_date,
            deadline=opportunity.deadline,
            expected_start_date=opportunity.expected_start_date,
            opportunity_type=opportunity.opportunity_type,
            lifecycle_status=opportunity.lifecycle_status,
            eligibility_status=result.decision.status,
            canonical_identity_key=opportunity.canonical_identity_key,
            source_status=opportunity.source_status,
        )
        self._opportunities.save(updated)
        return EligibilityEvaluationResult(
            decision=saved_decision,
            rule_results=saved_rules,
            opportunity=updated,
        )

    def list_decisions_for_opportunity(
        self, opportunity_id: str
    ) -> list[EligibilityDecision]:
        return self._decisions.list_for_opportunity(opportunity_id)
