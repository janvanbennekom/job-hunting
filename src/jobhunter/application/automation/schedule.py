"""Determine whether a scheduled automation run is due (external trigger friendly)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from jobhunter.infrastructure.automation.config import (
    ScheduleConfig,
    _parse_time_of_day,
    weekday_indices,
)

# Match external poll interval (e.g. Synology Task Scheduler every 15 minutes).
SCHEDULE_EXTERNAL_POLL_MINUTES = 15


def _normalize_instant(now: datetime | None) -> datetime:
    instant = now or datetime.now(tz=ZoneInfo("UTC"))
    if instant.tzinfo is None:
        return instant.replace(tzinfo=ZoneInfo("UTC"))
    return instant


def local_slot_start(schedule: ScheduleConfig, now: datetime) -> datetime | None:
    """Local timezone-aware start of today's configured slot, or None if wrong weekday."""
    if not schedule.enabled:
        return None
    tz = ZoneInfo(schedule.timezone)
    local = _normalize_instant(now).astimezone(tz)
    if local.weekday() not in weekday_indices(schedule.days_of_week):
        return None
    target_hour, target_minute = _parse_time_of_day(schedule.time_of_day)
    return local.replace(
        hour=target_hour,
        minute=target_minute,
        second=0,
        microsecond=0,
    )


def is_schedule_window_open(
    schedule: ScheduleConfig,
    *,
    now: datetime | None = None,
) -> bool:
    """True on a configured weekday at or after the configured local time (same calendar day)."""
    instant = _normalize_instant(now)
    slot_start = local_slot_start(schedule, instant)
    if slot_start is None:
        return False
    tz = ZoneInfo(schedule.timezone)
    local = instant.astimezone(tz)
    return local >= slot_start


def is_schedule_due(
    schedule: ScheduleConfig,
    *,
    now: datetime | None = None,
    session: Session | None = None,
) -> bool:
    """Return True when an external scheduler should start a scheduled apply run.

    Designed for polling (e.g. every 15 minutes): on Mon/Thu, any poll at or after
    08:00 Europe/Amsterdam opens the window until a successful scheduled run is
    recorded for that local calendar day (see AutomationRun idempotency).

    When ``session`` is provided, returns False if a SCHEDULED run with status
    SUCCESS or PARTIAL already started on this local day at or after the slot time.
    """
    if not schedule.enabled:
        return False
    if not is_schedule_window_open(schedule, now=now):
        return False
    if session is None:
        return True
    from jobhunter.infrastructure.persistence.automation_run_repository import (
        AutomationRunRepository,
    )

    instant = _normalize_instant(now)
    return not AutomationRunRepository(session).has_completed_scheduled_run_for_slot(
        schedule, instant
    )
