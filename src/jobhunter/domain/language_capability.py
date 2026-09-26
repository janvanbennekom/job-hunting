"""Professional language capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import prune_none


@dataclass(slots=True)
class LanguageCapability:
    """Language proficiency as stated in source material (no inferred CEFR)."""

    language: str
    id: str = field(default_factory=new_domain_id)
    proficiency_text: str | None = None
    cefr_level: str | None = None
    notes: str | None = None
    source_document_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.language = require_non_empty(self.language, "language")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "language": self.language,
                "proficiency_text": self.proficiency_text,
                "cefr_level": self.cefr_level,
                "notes": self.notes,
                "source_document_id": self.source_document_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> LanguageCapability:
        return cls(
            id=data["id"],
            language=data["language"],
            proficiency_text=data.get("proficiency_text"),
            cefr_level=data.get("cefr_level"),
            notes=data.get("notes"),
            source_document_id=data.get("source_document_id"),
        )
