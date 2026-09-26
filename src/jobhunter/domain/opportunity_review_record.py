"""Append-only human review judgment for an opportunity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.domain.serialization import (
    deserialize_datetime,
    enum_to_value,
    prune_none,
    serialize_datetime,
    value_to_enum,
)
from jobhunter.domain.validation import require_timezone_aware


@dataclass(slots=True)
class OpportunityReviewRecord:
    opportunity_id: str
    recorded_at: datetime
    disposition: ReviewDisposition
    id: str = field(default_factory=new_domain_id)
    notes: str | None = None
    search_strategy_revision_id: str | None = None
    profile_assessment_id: str | None = None
    ranking_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.recorded_at = require_timezone_aware(
            self.recorded_at, "recorded_at"
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "recorded_at": serialize_datetime(self.recorded_at),
                "disposition": enum_to_value(self.disposition),
                "notes": self.notes,
                "search_strategy_revision_id": self.search_strategy_revision_id,
                "profile_assessment_id": self.profile_assessment_id,
                "ranking_id": self.ranking_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunityReviewRecord:
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            recorded_at=deserialize_datetime(data["recorded_at"]),
            disposition=value_to_enum(ReviewDisposition, data["disposition"]),
            notes=data.get("notes"),
            search_strategy_revision_id=data.get("search_strategy_revision_id"),
            profile_assessment_id=data.get("profile_assessment_id"),
            ranking_id=data.get("ranking_id"),
        )
