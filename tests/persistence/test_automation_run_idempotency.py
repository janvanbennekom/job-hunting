"""Scheduled run slot idempotency (AutomationRun)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

from jobhunter.domain.automation_enums import (
    AutomationRunStatus,
    AutomationTriggerType,
)
from jobhunter.domain.automation_run import AutomationRun
from jobhunter.infrastructure.automation.config import ScheduleConfig
from jobhunter.infrastructure.persistence.automation_run_repository import (
    AutomationRunRepository,
)

pytestmark = pytest.mark.integration


def _schedule() -> ScheduleConfig:
    return ScheduleConfig(
        enabled=True,
        timezone="Europe/Amsterdam",
        days_of_week=("monday",),
        time_of_day="08:00",
    )


def test_has_completed_scheduled_run_for_slot(db_session: Session) -> None:
    repo = AutomationRunRepository(db_session)
    schedule = _schedule()
    # Monday 2026-09-28 08:30 Amsterdam
    now = datetime(2026, 9, 28, 6, 30, tzinfo=ZoneInfo("UTC"))
    assert not repo.has_completed_scheduled_run_for_slot(schedule, now)

    run = AutomationRun(
        started_at=datetime(2026, 9, 28, 6, 5, tzinfo=ZoneInfo("UTC")),
        trigger_type=AutomationTriggerType.SCHEDULED,
        status=AutomationRunStatus.SUCCESS,
    )
    repo.save(run)
    db_session.commit()

    assert repo.has_completed_scheduled_run_for_slot(schedule, now)
