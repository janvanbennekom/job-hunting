"""Thin repositories for Phase 1 domain entities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain import (
    JobSource,
    Opportunity,
    OpportunitySource,
    RawOpportunity,
)
from jobhunter.infrastructure.persistence import mappers
from jobhunter.infrastructure.persistence.models import (
    JobSourceRow,
    OpportunityRow,
    OpportunitySourceRow,
    RawOpportunityRow,
)


class JobSourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: JobSource) -> JobSource:
        row = mappers.job_source_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.job_source_to_domain(merged)

    def get_by_id(self, entity_id: str) -> JobSource | None:
        row = self._session.get(JobSourceRow, entity_id)
        if row is None:
            return None
        return mappers.job_source_to_domain(row)


class RawOpportunityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: RawOpportunity) -> RawOpportunity:
        row = mappers.raw_opportunity_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.raw_opportunity_to_domain(merged)

    def get_by_id(self, entity_id: str) -> RawOpportunity | None:
        row = self._session.get(RawOpportunityRow, entity_id)
        if row is None:
            return None
        return mappers.raw_opportunity_to_domain(row)


class OpportunityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: Opportunity) -> Opportunity:
        row = mappers.opportunity_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.opportunity_to_domain(merged)

    def get_by_id(self, entity_id: str) -> Opportunity | None:
        row = self._session.get(OpportunityRow, entity_id)
        if row is None:
            return None
        return mappers.opportunity_to_domain(row)


class OpportunitySourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunitySource) -> OpportunitySource:
        row = mappers.opportunity_source_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.opportunity_source_to_domain(merged)

    def get_by_id(self, entity_id: str) -> OpportunitySource | None:
        row = self._session.get(OpportunitySourceRow, entity_id)
        if row is None:
            return None
        return mappers.opportunity_source_to_domain(row)

    def list_for_opportunity(self, opportunity_id: str) -> list[OpportunitySource]:
        stmt = (
            select(OpportunitySourceRow)
            .where(OpportunitySourceRow.opportunity_id == opportunity_id)
            .order_by(OpportunitySourceRow.id)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.opportunity_source_to_domain(row) for row in rows]
