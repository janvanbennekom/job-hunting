"""Repositories for opportunity pursuit tracking."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.opportunity_pursuit import (
    OpportunityPursuit,
    OpportunityPursuitStatusEvent,
)
from jobhunter.infrastructure.persistence import pursuit_mappers as mappers
from jobhunter.infrastructure.persistence.models import (
    OpportunityPursuitRow,
    OpportunityPursuitStatusEventRow,
)


class OpportunityPursuitRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunityPursuit) -> OpportunityPursuit:
        row = mappers.pursuit_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.pursuit_to_domain(merged)

    def get_by_opportunity_id(
        self, opportunity_id: str
    ) -> OpportunityPursuit | None:
        stmt = select(OpportunityPursuitRow).where(
            OpportunityPursuitRow.opportunity_id == opportunity_id
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.pursuit_to_domain(row)

    def get_by_id(self, pursuit_id: str) -> OpportunityPursuit | None:
        row = self._session.get(OpportunityPursuitRow, pursuit_id)
        if row is None:
            return None
        return mappers.pursuit_to_domain(row)

    def list_all(self) -> list[OpportunityPursuit]:
        rows = self._session.scalars(select(OpportunityPursuitRow)).all()
        return [mappers.pursuit_to_domain(row) for row in rows]


class OpportunityPursuitStatusEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunityPursuitStatusEvent) -> OpportunityPursuitStatusEvent:
        row = mappers.pursuit_event_to_row(entity)
        self._session.add(row)
        self._session.flush()
        return mappers.pursuit_event_to_domain(row)

    def list_for_pursuit(
        self, pursuit_id: str
    ) -> list[OpportunityPursuitStatusEvent]:
        stmt = (
            select(OpportunityPursuitStatusEventRow)
            .where(OpportunityPursuitStatusEventRow.pursuit_id == pursuit_id)
            .order_by(
                OpportunityPursuitStatusEventRow.recorded_at.desc(),
                OpportunityPursuitStatusEventRow.id.desc(),
            )
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.pursuit_event_to_domain(row) for row in rows]
