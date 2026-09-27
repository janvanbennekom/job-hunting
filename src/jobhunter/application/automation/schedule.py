"""Determine whether a scheduled automation run is due (external trigger friendly)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from jobhunter.infrastructure.automation.config import (
    ScheduleConfig,
    _parse_time_of_day,
    weekday_indices,
)


def is_schedule_due(
    schedule: ScheduleConfig,
    *,
    now: datetime | None = None,
) -> bool:
    """Return True when `now` falls on a configured weekday at the configured local time.

    Comparison uses the configured timezone and matches hour:minute only (seconds
    ignored). When schedule.enabled is False, always returns False.
    """
    if not schedule.enabled:
        return False
    tz = ZoneInfo(schedule.timezone)
    instant = now or datetime.now(tz=ZoneInfo("UTC"))
    local = instant.astimezone(tz)
    if local.weekday() not in weekday_indices(schedule.days_of_week):
        return False
    target_hour, target_minute = _parse_time_of_day(schedule.time_of_day)
    return local.hour == target_hour and local.minute == target_minute
