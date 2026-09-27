"""Persistence for automation pipeline runs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.automation_run import AutomationRun
from jobhunter.infrastructure.persistence import mappers
from jobhunter.infrastructure.persistence.models import AutomationRunRow


class AutomationRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: AutomationRun) -> AutomationRun:
        row = mappers.automation_run_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.automation_run_to_domain(merged)

    def get_by_id(self, entity_id: str) -> AutomationRun | None:
        row = self._session.get(AutomationRunRow, entity_id)
        if row is None:
            return None
        return mappers.automation_run_to_domain(row)

    def list_recent(self, *, limit: int = 20) -> list[AutomationRun]:
        stmt = (
            select(AutomationRunRow)
            .order_by(AutomationRunRow.started_at.desc())
            .limit(limit)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.automation_run_to_domain(row) for row in rows]
