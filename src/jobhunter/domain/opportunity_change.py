"""Lightweight audit of a material change detected during processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.opportunity_enums import MaterialChangeField
from jobhunter.domain.serialization import (
    deserialize_datetime,
    enum_to_value,
    prune_none,
    serialize_datetime,
    value_to_enum,
)
from jobhunter.domain.validation import require_timezone_aware


@dataclass(slots=True)
class OpportunityChange:
    opportunity_id: str
    observation_id: str
    field_name: MaterialChangeField
    observed_at: datetime
    id: str = field(default_factory=new_domain_id)
    previous_value: str | None = None
    new_value: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.observation_id = require_non_empty(
            self.observation_id, "observation_id"
        )
        self.observed_at = require_timezone_aware(
            self.observed_at, "observed_at"
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "observation_id": self.observation_id,
                "field_name": enum_to_value(self.field_name),
                "previous_value": self.previous_value,
                "new_value": self.new_value,
                "observed_at": serialize_datetime(self.observed_at),
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunityChange:
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            observation_id=data["observation_id"],
            field_name=value_to_enum(MaterialChangeField, data["field_name"]),
            previous_value=data.get("previous_value"),
            new_value=data.get("new_value"),
            observed_at=deserialize_datetime(data["observed_at"]),
        )
