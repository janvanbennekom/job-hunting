"""Authoritative professional source document metadata (not file contents)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.profile_enums import ProfileDocumentType
from jobhunter.domain.serialization import enum_to_value, prune_none, value_to_enum


@dataclass(slots=True)
class ProfileDocument:
    """Reference to an authoritative profile source (CV, services doc, spreadsheet)."""

    document_type: ProfileDocumentType
    title: str
    id: str = field(default_factory=new_domain_id)
    source_reference: str | None = None
    version_label: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.title = require_non_empty(self.title, "title")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "document_type": enum_to_value(self.document_type),
                "title": self.title,
                "source_reference": self.source_reference,
                "version_label": self.version_label,
                "notes": self.notes,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ProfileDocument:
        return cls(
            id=data["id"],
            document_type=value_to_enum(
                ProfileDocumentType, data["document_type"]
            ),
            title=data["title"],
            source_reference=data.get("source_reference"),
            version_label=data.get("version_label"),
            notes=data.get("notes"),
        )
