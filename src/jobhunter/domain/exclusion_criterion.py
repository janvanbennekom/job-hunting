"""Explicit exclusion rule within a strategy revision."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import enum_to_value, prune_none, value_to_enum
from jobhunter.domain.strategy_enums import ExclusionCode
from jobhunter.domain.strategy_validation import validate_exclusion_parameters


@dataclass(frozen=True, slots=True)
class ExclusionCriterion:
    revision_id: str
    exclusion_code: ExclusionCode
    id: str = field(default_factory=new_domain_id)
    parameters: dict[str, Any] | None = None
    is_active: bool = True
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_non_empty(self.id, "id"))
        object.__setattr__(
            self, "revision_id", require_non_empty(self.revision_id, "revision_id")
        )
        object.__setattr__(
            self,
            "parameters",
            validate_exclusion_parameters(self.exclusion_code, self.parameters),
        )

    def to_mapping(self) -> dict[str, Any]:
        payload = prune_none(
            {
                "id": self.id,
                "revision_id": self.revision_id,
                "exclusion_code": enum_to_value(self.exclusion_code),
                "is_active": self.is_active,
                "notes": self.notes,
            }
        )
        if self.parameters is not None:
            payload["parameters"] = dict(self.parameters)
        return payload

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ExclusionCriterion:
        params = data.get("parameters")
        if params is not None:
            params = dict(params)
        return cls(
            id=data["id"],
            revision_id=data["revision_id"],
            exclusion_code=value_to_enum(ExclusionCode, data["exclusion_code"]),
            parameters=params,
            is_active=data.get("is_active", True),
            notes=data.get("notes"),
        )
