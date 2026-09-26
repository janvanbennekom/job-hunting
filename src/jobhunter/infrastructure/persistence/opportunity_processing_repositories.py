"""Repositories for opportunity observations and change audit."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.opportunity_change import OpportunityChange
from jobhunter.domain.opportunity_observation import OpportunityObservation
from jobhunter.infrastructure.persistence import mappers
from jobhunter.infrastructure.persistence.models import (
    OpportunityChangeRow,
    OpportunityObservationRow,
)


class OpportunityObservationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunityObservation) -> OpportunityObservation:
        row = mappers.opportunity_observation_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.opportunity_observation_to_domain(merged)

    def get_by_id(self, entity_id: str) -> OpportunityObservation | None:
        row = self._session.get(OpportunityObservationRow, entity_id)
        if row is None:
            return None
        return mappers.opportunity_observation_to_domain(row)

    def get_by_raw_opportunity_id(
        self, raw_opportunity_id: str
    ) -> OpportunityObservation | None:
        stmt = select(OpportunityObservationRow).where(
            OpportunityObservationRow.raw_opportunity_id == raw_opportunity_id
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.opportunity_observation_to_domain(row)

    def list_for_opportunity(
        self, opportunity_id: str
    ) -> list[OpportunityObservation]:
        stmt = (
            select(OpportunityObservationRow)
            .where(OpportunityObservationRow.opportunity_id == opportunity_id)
            .order_by(OpportunityObservationRow.observed_at)
        )
        rows = self._session.scalars(stmt).all()
        return [
            mappers.opportunity_observation_to_domain(row) for row in rows
        ]


class OpportunityChangeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunityChange) -> OpportunityChange:
        row = mappers.opportunity_change_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.opportunity_change_to_domain(merged)

    def list_for_observation(
        self, observation_id: str
    ) -> list[OpportunityChange]:
        stmt = (
            select(OpportunityChangeRow)
            .where(OpportunityChangeRow.observation_id == observation_id)
            .order_by(OpportunityChangeRow.field_name)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.opportunity_change_to_domain(row) for row in rows]

    def list_for_opportunity(self, opportunity_id: str) -> list[OpportunityChange]:
        stmt = (
            select(OpportunityChangeRow)
            .where(OpportunityChangeRow.opportunity_id == opportunity_id)
            .order_by(OpportunityChangeRow.observed_at)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.opportunity_change_to_domain(row) for row in rows]
