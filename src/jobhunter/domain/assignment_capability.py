"""Evidence link between an assignment and a capability classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import prune_none


@dataclass(slots=True)
class AssignmentCapability:
    """Assignment supports capability (many-to-many via explicit link)."""

    assignment_id: str
    capability_id: str
    id: str = field(default_factory=new_domain_id)
    source_document_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.assignment_id = require_non_empty(
            self.assignment_id, "assignment_id"
        )
        self.capability_id = require_non_empty(self.capability_id, "capability_id")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "assignment_id": self.assignment_id,
                "capability_id": self.capability_id,
                "source_document_id": self.source_document_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> AssignmentCapability:
        return cls(
            id=data["id"],
            assignment_id=data["assignment_id"],
            capability_id=data["capability_id"],
            source_document_id=data.get("source_document_id"),
        )
