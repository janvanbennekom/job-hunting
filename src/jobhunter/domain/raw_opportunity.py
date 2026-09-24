"""Source-acquired opportunity data before normalization."""

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
class RawOpportunity:
    """Raw source payload with provenance; values are not normalized."""

    source_id: str
    retrieved_at: datetime
    id: str = field(default_factory=new_domain_id)
    source_reference: str | None = None
    source_url: str | None = None
    raw_title: str | None = None
    raw_organisation: str | None = None
    raw_location: str | None = None
    raw_deadline: str | None = None
    raw_description: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.source_id = require_non_empty(self.source_id, "source_id")
        self.retrieved_at = require_timezone_aware(
            self.retrieved_at, "retrieved_at"
        )

    def to_mapping(self) -> dict[str, Any]:
        payload = prune_none(
            {
                "id": self.id,
                "source_id": self.source_id,
                "source_reference": self.source_reference,
                "source_url": self.source_url,
                "retrieved_at": serialize_datetime(self.retrieved_at),
                "raw_title": self.raw_title,
                "raw_organisation": self.raw_organisation,
                "raw_location": self.raw_location,
                "raw_deadline": self.raw_deadline,
                "raw_description": self.raw_description,
            }
        )
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> RawOpportunity:
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            source_reference=data.get("source_reference"),
            source_url=data.get("source_url"),
            retrieved_at=deserialize_datetime(data["retrieved_at"]),
            raw_title=data.get("raw_title"),
            raw_organisation=data.get("raw_organisation"),
            raw_location=data.get("raw_location"),
            raw_deadline=data.get("raw_deadline"),
            raw_description=data.get("raw_description"),
            extra=dict(data.get("extra") or {}),
        )
