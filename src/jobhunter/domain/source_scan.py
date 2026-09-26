"""Scan run metadata for an opportunity source."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import (
    deserialize_datetime,
    enum_to_value,
    prune_none,
    serialize_datetime,
    value_to_enum,
)
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.domain.validation import require_timezone_aware


@dataclass(slots=True)
class SourceScan:
    source_id: str
    started_at: datetime
    id: str = field(default_factory=new_domain_id)
    completed_at: datetime | None = None
    status: SourceScanStatus = SourceScanStatus.RUNNING
    records_retrieved: int = 0
    records_processed: int = 0
    records_failed: int = 0
    error_summary: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.source_id = require_non_empty(self.source_id, "source_id")
        self.started_at = require_timezone_aware(self.started_at, "started_at")
        if self.completed_at is not None:
            self.completed_at = require_timezone_aware(
                self.completed_at, "completed_at"
            )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "source_id": self.source_id,
                "started_at": serialize_datetime(self.started_at),
                "completed_at": (
                    serialize_datetime(self.completed_at)
                    if self.completed_at
                    else None
                ),
                "status": enum_to_value(self.status),
                "records_retrieved": self.records_retrieved,
                "records_processed": self.records_processed,
                "records_failed": self.records_failed,
                "error_summary": self.error_summary,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> SourceScan:
        completed = data.get("completed_at")
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            started_at=deserialize_datetime(data["started_at"]),
            completed_at=(
                deserialize_datetime(completed) if completed else None
            ),
            status=value_to_enum(SourceScanStatus, data["status"]),
            records_retrieved=int(data.get("records_retrieved", 0)),
            records_processed=int(data.get("records_processed", 0)),
            records_failed=int(data.get("records_failed", 0)),
            error_summary=data.get("error_summary"),
        )
