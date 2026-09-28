"""Persistence for automation pipeline runs."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.application.automation.schedule import local_slot_start
from jobhunter.domain.automation_enums import AutomationRunStatus, AutomationTriggerType
from jobhunter.domain.automation_run import AutomationRun
from jobhunter.infrastructure.automation.config import ScheduleConfig
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

    def has_completed_scheduled_run_for_slot(
        self,
        schedule: ScheduleConfig,
        now: datetime,
    ) -> bool:
        """True if a SCHEDULED SUCCESS/PARTIAL run already satisfied today's slot."""
        slot_start = local_slot_start(schedule, now)
        if slot_start is None:
            return False
        tz = ZoneInfo(schedule.timezone)
        if now.tzinfo is None:
            instant = now.replace(tzinfo=ZoneInfo("UTC"))
        else:
            instant = now
        local = instant.astimezone(tz)
        day_start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        slot_start_utc = slot_start.astimezone(ZoneInfo("UTC"))
        day_end_utc = day_end.astimezone(ZoneInfo("UTC"))
        stmt = (
            select(AutomationRunRow.id)
            .where(
                AutomationRunRow.trigger_type == AutomationTriggerType.SCHEDULED.value,
                AutomationRunRow.status.in_(
                    (
                        AutomationRunStatus.SUCCESS.value,
                        AutomationRunStatus.PARTIAL.value,
                    )
                ),
                AutomationRunRow.started_at >= slot_start_utc,
                AutomationRunRow.started_at < day_end_utc,
            )
            .limit(1)
        )
        return self._session.scalar(stmt) is not None
