"""Append-only processing observation for a canonical opportunity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.enums import LifecycleStatus
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
class OpportunityObservation:
    """Point-in-time evidence linking raw retrieval to a canonical opportunity."""

    opportunity_id: str
    raw_opportunity_id: str
    observed_at: datetime
    lifecycle_status: LifecycleStatus
    id: str = field(default_factory=new_domain_id)

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.raw_opportunity_id = require_non_empty(
            self.raw_opportunity_id, "raw_opportunity_id"
        )
        self.observed_at = require_timezone_aware(
            self.observed_at, "observed_at"
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "raw_opportunity_id": self.raw_opportunity_id,
                "observed_at": serialize_datetime(self.observed_at),
                "lifecycle_status": enum_to_value(self.lifecycle_status),
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunityObservation:
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            raw_opportunity_id=data["raw_opportunity_id"],
            observed_at=deserialize_datetime(data["observed_at"]),
            lifecycle_status=value_to_enum(
                LifecycleStatus, data["lifecycle_status"]
            ),
        )
