"""Market-facing professional service offering (distinct from Capability)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import prune_none


@dataclass(slots=True)
class ProfessionalService:
    """Service the consultant offers (sourced primarily from Professional Services)."""

    name: str
    id: str = field(default_factory=new_domain_id)
    description: str | None = None
    is_active: bool = True
    source_document_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.name = require_non_empty(self.name, "name")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "is_active": self.is_active,
                "source_document_id": self.source_document_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ProfessionalService:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            is_active=data.get("is_active", True),
            source_document_id=data.get("source_document_id"),
        )
