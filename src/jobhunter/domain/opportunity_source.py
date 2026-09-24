"""Link between a canonical opportunity and a configured source."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import (
    deserialize_datetime,
    prune_none,
    serialize_datetime,
)
from jobhunter.domain.validation import require_timezone_aware


@dataclass(slots=True)
class OpportunitySource:
    """Source-specific provenance for an opportunity (many sources per opportunity)."""

    opportunity_id: str
    source_id: str
    id: str = field(default_factory=new_domain_id)
    source_reference: str | None = None
    source_url: str | None = None
    original_url: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.source_id = require_non_empty(self.source_id, "source_id")
        if self.first_seen_at is not None:
            self.first_seen_at = require_timezone_aware(
                self.first_seen_at, "first_seen_at"
            )
        if self.last_seen_at is not None:
            self.last_seen_at = require_timezone_aware(
                self.last_seen_at, "last_seen_at"
            )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "source_id": self.source_id,
                "source_reference": self.source_reference,
                "source_url": self.source_url,
                "original_url": self.original_url,
                "first_seen_at": (
                    serialize_datetime(self.first_seen_at)
                    if self.first_seen_at
                    else None
                ),
                "last_seen_at": (
                    serialize_datetime(self.last_seen_at)
                    if self.last_seen_at
                    else None
                ),
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunitySource:
        first_seen = data.get("first_seen_at")
        last_seen = data.get("last_seen_at")
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            source_id=data["source_id"],
            source_reference=data.get("source_reference"),
            source_url=data.get("source_url"),
            original_url=data.get("original_url"),
            first_seen_at=(
                deserialize_datetime(first_seen) if first_seen else None
            ),
            last_seen_at=(
                deserialize_datetime(last_seen) if last_seen else None
            ),
        )
