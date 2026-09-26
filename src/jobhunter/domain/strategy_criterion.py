"""Strategy preference or hard constraint within a revision.

PreferenceStrength on StrategyCriterion applies only to single-aspect preference
criteria (for example travel pattern or duration band). Multi-aspect preferences
store strengths inside the typed value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import enum_to_value, prune_none, value_to_enum
from jobhunter.domain.strategy_criterion_values import (
    CriterionValue,
    criterion_value_to_mapping,
    parse_criterion_value,
)
from jobhunter.domain.strategy_enums import (
    PreferenceStrength,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.domain.strategy_validation import (
    require_non_negative_int,
    validate_criterion_strength_semantics,
)


@dataclass(frozen=True, slots=True)
class StrategyCriterion:
    revision_id: str
    category: StrategyCriterionCategory
    code: StrategyParameterCode
    value: CriterionValue
    id: str = field(default_factory=new_domain_id)
    strength: PreferenceStrength | None = None
    is_active: bool = True
    notes: str | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_non_empty(self.id, "id"))
        object.__setattr__(
            self, "revision_id", require_non_empty(self.revision_id, "revision_id")
        )
        object.__setattr__(
            self, "sort_order", require_non_negative_int(self.sort_order, "sort_order")
        )
        validate_criterion_strength_semantics(self.category, self.code, self.strength)

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "revision_id": self.revision_id,
                "category": enum_to_value(self.category),
                "code": enum_to_value(self.code),
                "value": criterion_value_to_mapping(self.value),
                "strength": (
                    enum_to_value(self.strength) if self.strength is not None else None
                ),
                "is_active": self.is_active,
                "notes": self.notes,
                "sort_order": self.sort_order,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> StrategyCriterion:
        category = value_to_enum(StrategyCriterionCategory, data["category"])
        code = value_to_enum(StrategyParameterCode, data["code"])
        raw_value = data.get("value")
        if not isinstance(raw_value, dict):
            raise ValueError("value must be a mapping")
        strength_raw = data.get("strength")
        strength = (
            value_to_enum(PreferenceStrength, strength_raw)
            if strength_raw is not None
            else None
        )
        return cls(
            id=data["id"],
            revision_id=data["revision_id"],
            category=category,
            code=code,
            value=parse_criterion_value(category, code, raw_value),
            strength=strength,
            is_active=data.get("is_active", True),
            notes=data.get("notes"),
            sort_order=data.get("sort_order", 0),
        )
