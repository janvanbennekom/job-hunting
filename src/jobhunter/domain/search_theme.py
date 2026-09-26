"""Positive search theme within a strategy revision."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import enum_to_value, prune_none, value_to_enum
from jobhunter.domain.strategy_enums import PreferenceStrength
from jobhunter.domain.strategy_validation import require_non_negative_int


@dataclass(frozen=True, slots=True)
class SearchTheme:
    revision_id: str
    theme_key: str
    label: str
    strength: PreferenceStrength
    id: str = field(default_factory=new_domain_id)
    is_active: bool = True
    notes: str | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_non_empty(self.id, "id"))
        object.__setattr__(
            self, "revision_id", require_non_empty(self.revision_id, "revision_id")
        )
        object.__setattr__(
            self, "theme_key", require_non_empty(self.theme_key, "theme_key")
        )
        object.__setattr__(self, "label", require_non_empty(self.label, "label"))
        object.__setattr__(
            self, "sort_order", require_non_negative_int(self.sort_order, "sort_order")
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "revision_id": self.revision_id,
                "theme_key": self.theme_key,
                "label": self.label,
                "strength": enum_to_value(self.strength),
                "is_active": self.is_active,
                "notes": self.notes,
                "sort_order": self.sort_order,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> SearchTheme:
        return cls(
            id=data["id"],
            revision_id=data["revision_id"],
            theme_key=data["theme_key"],
            label=data["label"],
            strength=value_to_enum(PreferenceStrength, data["strength"]),
            is_active=data.get("is_active", True),
            notes=data.get("notes"),
            sort_order=data.get("sort_order", 0),
        )
