"""Repositories for eligibility decisions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.eligibility_decision import EligibilityDecision
from jobhunter.domain.eligibility_rule_result import EligibilityRuleResult
from jobhunter.infrastructure.persistence import eligibility_mappers as mappers
from jobhunter.infrastructure.persistence.models import (
    EligibilityDecisionRow,
    EligibilityRuleResultRow,
)


class EligibilityDecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: EligibilityDecision) -> EligibilityDecision:
        row = mappers.eligibility_decision_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.eligibility_decision_to_domain(merged)

    def get_by_id(self, entity_id: str) -> EligibilityDecision | None:
        row = self._session.get(EligibilityDecisionRow, entity_id)
        if row is None:
            return None
        return mappers.eligibility_decision_to_domain(row)

    def list_for_opportunity(self, opportunity_id: str) -> list[EligibilityDecision]:
        stmt = (
            select(EligibilityDecisionRow)
            .where(EligibilityDecisionRow.opportunity_id == opportunity_id)
            .order_by(EligibilityDecisionRow.evaluated_at)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.eligibility_decision_to_domain(row) for row in rows]


class EligibilityRuleResultRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: EligibilityRuleResult) -> EligibilityRuleResult:
        row = mappers.eligibility_rule_result_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.eligibility_rule_result_to_domain(merged)

    def list_for_decision(self, decision_id: str) -> list[EligibilityRuleResult]:
        stmt = (
            select(EligibilityRuleResultRow)
            .where(EligibilityRuleResultRow.decision_id == decision_id)
            .order_by(EligibilityRuleResultRow.rule_kind, EligibilityRuleResultRow.rule_code)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.eligibility_rule_result_to_domain(row) for row in rows]
