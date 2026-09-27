"""Schedule due detection tests."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from jobhunter.application.automation.schedule import is_schedule_due
from jobhunter.infrastructure.automation.config import ScheduleConfig


def test_monday_0800_amsterdam_due() -> None:
    schedule = ScheduleConfig(
        enabled=True,
        timezone="Europe/Amsterdam",
        days_of_week=("monday",),
        time_of_day="08:00",
    )
    # 2026-09-28 is a Monday
    instant = datetime(2026, 9, 28, 6, 0, tzinfo=ZoneInfo("UTC"))
    assert is_schedule_due(schedule, now=instant)


def test_wrong_day_not_due() -> None:
    schedule = ScheduleConfig(
        enabled=True,
        timezone="Europe/Amsterdam",
        days_of_week=("thursday",),
        time_of_day="08:00",
    )
    instant = datetime(2026, 9, 28, 6, 0, tzinfo=ZoneInfo("UTC"))
    assert not is_schedule_due(schedule, now=instant)


def test_disabled_schedule_never_due() -> None:
    schedule = ScheduleConfig(enabled=False)
    instant = datetime(2026, 9, 28, 6, 0, tzinfo=ZoneInfo("UTC"))
    assert not is_schedule_due(schedule, now=instant)
