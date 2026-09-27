"""Persisted record of a multi-source automation pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.automation_enums import (
    AutomationRunStatus,
    AutomationTriggerType,
)
from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import (
    deserialize_datetime,
    enum_to_value,
    prune_none,
    serialize_datetime,
    value_to_enum,
)
from jobhunter.domain.validation import require_timezone_aware


@dataclass(slots=True)
class AutomationRun:
    started_at: datetime
    trigger_type: AutomationTriggerType
    id: str = field(default_factory=new_domain_id)
    completed_at: datetime | None = None
    status: AutomationRunStatus = AutomationRunStatus.RUNNING
    config_snapshot: dict[str, Any] = field(default_factory=dict)
    source_scan_ids: list[str] = field(default_factory=list)
    records_retrieved: int = 0
    records_processed: int = 0
    records_failed: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    error_summary: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.started_at = require_timezone_aware(self.started_at, "started_at")
        if self.completed_at is not None:
            self.completed_at = require_timezone_aware(
                self.completed_at, "completed_at"
            )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "started_at": serialize_datetime(self.started_at),
                "completed_at": (
                    serialize_datetime(self.completed_at)
                    if self.completed_at
                    else None
                ),
                "status": enum_to_value(self.status),
                "trigger_type": enum_to_value(self.trigger_type),
                "config_snapshot": self.config_snapshot,
                "source_scan_ids": self.source_scan_ids,
                "records_retrieved": self.records_retrieved,
                "records_processed": self.records_processed,
                "records_failed": self.records_failed,
                "sources_succeeded": self.sources_succeeded,
                "sources_failed": self.sources_failed,
                "error_summary": self.error_summary,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> AutomationRun:
        completed = data.get("completed_at")
        return cls(
            id=data["id"],
            started_at=deserialize_datetime(data["started_at"]),
            completed_at=(
                deserialize_datetime(completed) if completed else None
            ),
            status=value_to_enum(AutomationRunStatus, data["status"]),
            trigger_type=value_to_enum(
                AutomationTriggerType, data["trigger_type"]
            ),
            config_snapshot=dict(data.get("config_snapshot") or {}),
            source_scan_ids=list(data.get("source_scan_ids") or []),
            records_retrieved=int(data.get("records_retrieved", 0)),
            records_processed=int(data.get("records_processed", 0)),
            records_failed=int(data.get("records_failed", 0)),
            sources_succeeded=int(data.get("sources_succeeded", 0)),
            sources_failed=int(data.get("sources_failed", 0)),
            error_summary=data.get("error_summary"),
        )
