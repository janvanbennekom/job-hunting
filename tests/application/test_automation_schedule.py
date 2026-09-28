"""Schedule due detection tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from jobhunter.application.automation.schedule import (
    is_schedule_due,
    is_schedule_window_open,
    local_slot_start,
)
from jobhunter.infrastructure.automation.config import ScheduleConfig


def _monday_schedule() -> ScheduleConfig:
    return ScheduleConfig(
        enabled=True,
        timezone="Europe/Amsterdam",
        days_of_week=("monday", "thursday"),
        time_of_day="08:00",
    )


def test_monday_0800_amsterdam_window_open() -> None:
    schedule = _monday_schedule()
    # 2026-09-28 is a Monday; 06:00 UTC = 08:00 CEST
    instant = datetime(2026, 9, 28, 6, 0, tzinfo=ZoneInfo("UTC"))
    assert local_slot_start(schedule, instant) is not None
    assert is_schedule_window_open(schedule, now=instant)
    assert is_schedule_due(schedule, now=instant)


def test_monday_0815_still_due_without_idempotency_check() -> None:
    schedule = _monday_schedule()
    instant = datetime(2026, 9, 28, 6, 15, tzinfo=ZoneInfo("UTC"))
    assert is_schedule_window_open(schedule, now=instant)
    assert is_schedule_due(schedule, now=instant)


def test_monday_0745_not_due() -> None:
    schedule = _monday_schedule()
    instant = datetime(2026, 9, 28, 5, 45, tzinfo=ZoneInfo("UTC"))
    assert not is_schedule_window_open(schedule, now=instant)
    assert not is_schedule_due(schedule, now=instant)


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


def test_idempotency_blocks_second_poll_same_day() -> None:
    schedule = _monday_schedule()
    instant = datetime(2026, 9, 28, 6, 15, tzinfo=ZoneInfo("UTC"))
    session = MagicMock()
    repo = MagicMock()
    repo.has_completed_scheduled_run_for_slot.return_value = True
    with patch(
        "jobhunter.infrastructure.persistence.automation_run_repository.AutomationRunRepository",
        return_value=repo,
    ):
        assert not is_schedule_due(schedule, now=instant, session=session)
