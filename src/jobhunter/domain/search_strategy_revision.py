"""Immutable search strategy revision metadata (Phase 4)."""

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
from jobhunter.domain.strategy_enums import RevisionChangeSource, RevisionStatus
from jobhunter.domain.strategy_validation import (
    require_content_hash,
    require_positive_int,
)
from jobhunter.domain.validation import require_timezone_aware


@dataclass(frozen=True, slots=True)
class SearchStrategyRevision:
    """Immutable strategy snapshot identity and metadata."""

    search_strategy_id: str
    revision_number: int
    status: RevisionStatus
    created_at: datetime
    change_summary: str
    change_source: RevisionChangeSource
    content_hash: str
    id: str = field(default_factory=new_domain_id)
    supersedes_revision_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_non_empty(self.id, "id"))
        object.__setattr__(
            self,
            "search_strategy_id",
            require_non_empty(self.search_strategy_id, "search_strategy_id"),
        )
        object.__setattr__(
            self,
            "revision_number",
            require_positive_int(self.revision_number, "revision_number"),
        )
        object.__setattr__(
            self,
            "created_at",
            require_timezone_aware(self.created_at, "created_at"),
        )
        object.__setattr__(
            self,
            "change_summary",
            require_non_empty(self.change_summary, "change_summary"),
        )
        object.__setattr__(
            self,
            "content_hash",
            require_content_hash(self.content_hash),
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "search_strategy_id": self.search_strategy_id,
                "revision_number": self.revision_number,
                "status": enum_to_value(self.status),
                "created_at": serialize_datetime(self.created_at),
                "change_summary": self.change_summary,
                "change_source": enum_to_value(self.change_source),
                "supersedes_revision_id": self.supersedes_revision_id,
                "content_hash": self.content_hash,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> SearchStrategyRevision:
        return cls(
            id=data["id"],
            search_strategy_id=data["search_strategy_id"],
            revision_number=data["revision_number"],
            status=value_to_enum(RevisionStatus, data["status"]),
            created_at=deserialize_datetime(data["created_at"]),
            change_summary=data["change_summary"],
            change_source=value_to_enum(RevisionChangeSource, data["change_source"]),
            supersedes_revision_id=data.get("supersedes_revision_id"),
            content_hash=data["content_hash"],
        )
