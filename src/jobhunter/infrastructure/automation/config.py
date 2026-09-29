"""Load and validate automation / scheduling configuration (JSON file + env path)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_SOURCE_ID
from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID
from jobhunter.connectors.afdb.identity import AFDB_CONSULTANTS_SOURCE_ID
from jobhunter.connectors.undp.identity import UNDP_JOBS_SOURCE_ID
from jobhunter.connectors.reliefweb.identity import RELIEFWEB_JOBS_SOURCE_ID
from jobhunter.connectors.ted.identity import TED_EU_PROCUREMENT_SOURCE_ID
from jobhunter.connectors.worldbank.identity import WORLDBANK_PROCUREMENT_SOURCE_ID

_ENV_CONFIG_PATH = "JOBHUNTER_AUTOMATION_CONFIG"

_DAY_ALIASES = {
    "mon": "monday",
    "monday": "monday",
    "tue": "tuesday",
    "tues": "tuesday",
    "tuesday": "tuesday",
    "wed": "wednesday",
    "wednesday": "wednesday",
    "thu": "thursday",
    "thur": "thursday",
    "thurs": "thursday",
    "thursday": "thursday",
    "fri": "friday",
    "friday": "friday",
    "sat": "saturday",
    "saturday": "saturday",
    "sun": "sunday",
    "sunday": "sunday",
}

_WEEKDAY_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

KNOWN_SOURCE_KEYS = frozenset(
    {
        "fao",
        "developmentaid",
        "worldbank",
        "undp",
        "afdb",
        "reliefweb",
        "ted",
    }
)

SOURCE_KEY_TO_JOB_SOURCE_ID = {
    "fao": FAO_JOBS_SOURCE_ID,
    "developmentaid": DEVELOPMENTAID_JOBS_SOURCE_ID,
    "worldbank": WORLDBANK_PROCUREMENT_SOURCE_ID,
    "undp": UNDP_JOBS_SOURCE_ID,
    "afdb": AFDB_CONSULTANTS_SOURCE_ID,
    "reliefweb": RELIEFWEB_JOBS_SOURCE_ID,
    "ted": TED_EU_PROCUREMENT_SOURCE_ID,
}


@dataclass(frozen=True, slots=True)
class SourceAutomationConfig:
    key: str
    enabled: bool = True
    keyword: str = ""
    limit: int = 25
    fetch_details: bool = True

    def sanitized_snapshot(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "enabled": self.enabled,
            "keyword": self.keyword,
            "limit": self.limit,
            "fetch_details": self.fetch_details,
        }


@dataclass(frozen=True, slots=True)
class ScheduleConfig:
    enabled: bool = True
    timezone: str = "Europe/Amsterdam"
    days_of_week: tuple[str, ...] = ("monday", "thursday")
    time_of_day: str = "08:00"

    def sanitized_snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "timezone": self.timezone,
            "days_of_week": list(self.days_of_week),
            "time_of_day": self.time_of_day,
        }


@dataclass(frozen=True, slots=True)
class PipelineAutomationConfig:
    production_assessment_enabled: bool = False
    assessment_required: bool = False
    ranking_enabled: bool = True

    def sanitized_snapshot(self) -> dict[str, Any]:
        return {
            "production_assessment_enabled": self.production_assessment_enabled,
            "assessment_required": self.assessment_required,
            "ranking_enabled": self.ranking_enabled,
        }


@dataclass(frozen=True, slots=True)
class NotificationAutomationConfig:
    enabled: bool = True
    high_ranking_alerts_enabled: bool = True

    def sanitized_snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "high_ranking_alerts_enabled": self.high_ranking_alerts_enabled,
        }


@dataclass(frozen=True, slots=True)
class AutomationConfig:
    schedule: ScheduleConfig
    pipeline: PipelineAutomationConfig
    notifications: NotificationAutomationConfig
    sources: tuple[SourceAutomationConfig, ...]

    def sanitized_snapshot(self) -> dict[str, Any]:
        return {
            "schedule": self.schedule.sanitized_snapshot(),
            "pipeline": self.pipeline.sanitized_snapshot(),
            "notifications": self.notifications.sanitized_snapshot(),
            "sources": [s.sanitized_snapshot() for s in self.sources],
        }

    def enabled_sources(self) -> tuple[SourceAutomationConfig, ...]:
        return tuple(s for s in self.sources if s.enabled)


def default_automation_config() -> AutomationConfig:
    return AutomationConfig(
        schedule=ScheduleConfig(),
        pipeline=PipelineAutomationConfig(),
        notifications=NotificationAutomationConfig(),
        sources=(
            SourceAutomationConfig(key="fao", enabled=True, limit=25),
            SourceAutomationConfig(
                key="developmentaid", enabled=True, limit=25, fetch_details=True
            ),
        ),
    )


def _parse_time_of_day(value: str) -> tuple[int, int]:
    text = value.strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"time_of_day must be HH:MM (24h), got {value!r}"
        )
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"time_of_day out of range: {value!r}")
    return hour, minute


def _normalize_day(name: str) -> str:
    key = name.strip().lower()
    normalized = _DAY_ALIASES.get(key)
    if normalized is None:
        raise ValueError(f"Unknown day_of_week: {name!r}")
    return normalized


def weekday_indices(days: tuple[str, ...]) -> frozenset[int]:
    return frozenset(_WEEKDAY_TO_INDEX[d] for d in days)


def parse_schedule_config(data: Mapping[str, Any]) -> ScheduleConfig:
    enabled = bool(data.get("enabled", True))
    timezone = str(data.get("timezone", "Europe/Amsterdam")).strip()
    if not timezone:
        raise ValueError("schedule.timezone must be non-empty")
    raw_days = data.get("days_of_week", ["monday", "thursday"])
    if not isinstance(raw_days, list) or not raw_days:
        raise ValueError("schedule.days_of_week must be a non-empty list")
    days = tuple(_normalize_day(str(d)) for d in raw_days)
    time_of_day = str(data.get("time_of_day", "08:00"))
    _parse_time_of_day(time_of_day)
    return ScheduleConfig(
        enabled=enabled,
        timezone=timezone,
        days_of_week=days,
        time_of_day=time_of_day,
    )


def parse_source_config(data: Mapping[str, Any]) -> SourceAutomationConfig:
    key = str(data.get("key", "")).strip().lower()
    if key not in KNOWN_SOURCE_KEYS:
        raise ValueError(
            f"Unknown source key {key!r}; known: {sorted(KNOWN_SOURCE_KEYS)}"
        )
    limit = int(data.get("limit", 25))
    if limit < 1 or limit > 500:
        raise ValueError("source.limit must be between 1 and 500")
    return SourceAutomationConfig(
        key=key,
        enabled=bool(data.get("enabled", True)),
        keyword=str(data.get("keyword", "") or ""),
        limit=limit,
        fetch_details=bool(data.get("fetch_details", True)),
    )


def parse_automation_config(data: Mapping[str, Any]) -> AutomationConfig:
    schedule = parse_schedule_config(data.get("schedule") or {})
    pipeline_raw = data.get("pipeline") or {}
    pipeline = PipelineAutomationConfig(
        production_assessment_enabled=bool(
            pipeline_raw.get("production_assessment_enabled", False)
        ),
        assessment_required=bool(pipeline_raw.get("assessment_required", False)),
        ranking_enabled=bool(pipeline_raw.get("ranking_enabled", True)),
    )
    notifications_raw = data.get("notifications") or {}
    notifications = NotificationAutomationConfig(
        enabled=bool(notifications_raw.get("enabled", True)),
        high_ranking_alerts_enabled=bool(
            notifications_raw.get("high_ranking_alerts_enabled", True)
        ),
    )
    sources_raw = data.get("sources")
    if not sources_raw:
        sources = default_automation_config().sources
    else:
        if not isinstance(sources_raw, list):
            raise ValueError("sources must be a list")
        sources = tuple(parse_source_config(item) for item in sources_raw)
    return AutomationConfig(
        schedule=schedule,
        pipeline=pipeline,
        notifications=notifications,
        sources=sources,
    )


def load_automation_config(
    *,
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> AutomationConfig:
    env_map = environ if environ is not None else os.environ
    resolved_path = path
    if resolved_path is None:
        env_path = env_map.get(_ENV_CONFIG_PATH)
        if env_path:
            resolved_path = Path(env_path)
    if resolved_path is None or not resolved_path.exists():
        return default_automation_config()
    payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Automation config root must be a JSON object")
    return parse_automation_config(payload)


def resolve_config_path(environ: Mapping[str, str] | None = None) -> Path | None:
    env_map = environ if environ is not None else os.environ
    env_path = env_map.get(_ENV_CONFIG_PATH)
    if env_path:
        return Path(env_path)
    return None
