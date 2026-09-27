"""Automation configuration parsing tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jobhunter.infrastructure.automation.config import (
    default_automation_config,
    load_automation_config,
    parse_automation_config,
    parse_schedule_config,
)


def test_default_config_monday_thursday_amsterdam() -> None:
    cfg = default_automation_config()
    assert cfg.schedule.timezone == "Europe/Amsterdam"
    assert cfg.schedule.days_of_week == ("monday", "thursday")
    assert cfg.schedule.time_of_day == "08:00"
    keys = {s.key for s in cfg.sources}
    assert keys == {"fao", "developmentaid"}


def test_parse_schedule_days_and_time() -> None:
    schedule = parse_schedule_config(
        {
            "days_of_week": ["Mon", "Thu"],
            "time_of_day": "09:30",
            "timezone": "UTC",
        }
    )
    assert schedule.days_of_week == ("monday", "thursday")
    assert schedule.time_of_day == "09:30"


def test_invalid_source_key_raises() -> None:
    with pytest.raises(ValueError, match="Unknown source key"):
        parse_automation_config(
            {"sources": [{"key": "devex", "enabled": True}]}
        )


def test_example_json_round_trip(tmp_path: Path) -> None:
    example = Path("config/automation.example.json")
    payload = json.loads(example.read_text(encoding="utf-8"))
    cfg = parse_automation_config(payload)
    assert cfg.pipeline.ranking_enabled is True
    path = tmp_path / "automation.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_automation_config(path=path)
    assert loaded.schedule.timezone == cfg.schedule.timezone
