"""Root professional evidence representation for the user."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import prune_none


@dataclass(slots=True)
class ProfessionalProfile:
    """What the user can credibly claim (not current search preferences)."""

    display_name: str
    id: str = field(default_factory=new_domain_id)
    positioning_summary: str | None = None
    primary_cv_document_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.display_name = require_non_empty(self.display_name, "display_name")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "display_name": self.display_name,
                "positioning_summary": self.positioning_summary,
                "primary_cv_document_id": self.primary_cv_document_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ProfessionalProfile:
        return cls(
            id=data["id"],
            display_name=data["display_name"],
            positioning_summary=data.get("positioning_summary"),
            primary_cv_document_id=data.get("primary_cv_document_id"),
        )
