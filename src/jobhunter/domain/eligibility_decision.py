"""Auditable eligibility evaluation for an opportunity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.enums import EligibilityStatus
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
class EligibilityDecision:
    opportunity_id: str
    search_strategy_revision_id: str
    evaluated_at: datetime
    status: EligibilityStatus
    id: str = field(default_factory=new_domain_id)

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.search_strategy_revision_id = require_non_empty(
            self.search_strategy_revision_id, "search_strategy_revision_id"
        )
        self.evaluated_at = require_timezone_aware(
            self.evaluated_at, "evaluated_at"
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "search_strategy_revision_id": self.search_strategy_revision_id,
                "evaluated_at": serialize_datetime(self.evaluated_at),
                "status": enum_to_value(self.status),
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> EligibilityDecision:
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            search_strategy_revision_id=data["search_strategy_revision_id"],
            evaluated_at=deserialize_datetime(data["evaluated_at"]),
            status=value_to_enum(EligibilityStatus, data["status"]),
        )
