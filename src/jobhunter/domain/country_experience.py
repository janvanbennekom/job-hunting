"""Evidence of professional work experience in a country."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import prune_none


@dataclass(slots=True)
class CountryExperience:
    """Country where the consultant has professional work experience (sourced evidence)."""

    country: str
    id: str = field(default_factory=new_domain_id)
    notes: str | None = None
    source_document_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.country = require_non_empty(self.country, "country")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "country": self.country,
                "notes": self.notes,
                "source_document_id": self.source_document_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> CountryExperience:
        return cls(
            id=data["id"],
            country=data["country"],
            notes=data.get("notes"),
            source_document_id=data.get("source_document_id"),
        )
