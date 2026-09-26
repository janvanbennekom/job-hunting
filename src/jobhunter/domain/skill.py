"""Technical or professional skill / technology (distinct from Capability)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import prune_none


@dataclass(slots=True)
class Skill:
    """Skill or technology used in delivery (e.g. PostgreSQL, QGIS)."""

    name: str
    id: str = field(default_factory=new_domain_id)
    category: str | None = None
    description: str | None = None
    source_document_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.name = require_non_empty(self.name, "name")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "name": self.name,
                "category": self.category,
                "description": self.description,
                "source_document_id": self.source_document_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Skill:
        return cls(
            id=data["id"],
            name=data["name"],
            category=data.get("category"),
            description=data.get("description"),
            source_document_id=data.get("source_document_id"),
        )
