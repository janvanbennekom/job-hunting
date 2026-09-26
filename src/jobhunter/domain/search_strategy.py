"""Stable search strategy identity (Phase 4)."""

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
class SearchStrategy:
    """Logical search strategy for one user; points at the active revision."""

    owner_key: str
    id: str = field(default_factory=new_domain_id)
    current_revision_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.owner_key = require_non_empty(self.owner_key, "owner_key")
        if self.created_at is not None:
            self.created_at = require_timezone_aware(self.created_at, "created_at")
        if self.updated_at is not None:
            self.updated_at = require_timezone_aware(self.updated_at, "updated_at")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "owner_key": self.owner_key,
                "current_revision_id": self.current_revision_id,
                "created_at": (
                    serialize_datetime(self.created_at)
                    if self.created_at is not None
                    else None
                ),
                "updated_at": (
                    serialize_datetime(self.updated_at)
                    if self.updated_at is not None
                    else None
                ),
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> SearchStrategy:
        created = data.get("created_at")
        updated = data.get("updated_at")
        return cls(
            id=data["id"],
            owner_key=data["owner_key"],
            current_revision_id=data.get("current_revision_id"),
            created_at=deserialize_datetime(created) if created else None,
            updated_at=deserialize_datetime(updated) if updated else None,
        )
