"""Controlled classification of professional project experience."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.profile_enums import CapabilityCategory
from jobhunter.domain.serialization import enum_to_value, prune_none, value_to_enum


@dataclass(slots=True)
class Capability:
    """Experience capability (e.g. system integration), not a skill or service."""

    code: str
    name: str
    category: CapabilityCategory
    id: str = field(default_factory=new_domain_id)
    description: str | None = None
    is_active: bool = True
    source_document_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.code = require_non_empty(self.code, "code")
        self.name = require_non_empty(self.name, "name")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "code": self.code,
                "name": self.name,
                "category": enum_to_value(self.category),
                "description": self.description,
                "is_active": self.is_active,
                "source_document_id": self.source_document_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Capability:
        return cls(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            category=value_to_enum(CapabilityCategory, data["category"]),
            description=data.get("description"),
            is_active=data.get("is_active", True),
            source_document_id=data.get("source_document_id"),
        )
