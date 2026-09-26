"""Professional assignment / project evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import prune_none


def _validate_non_negative_days(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError("working_days must be non-negative")
    return value


@dataclass(slots=True)
class Assignment:
    """Structured project experience (primary source: Project worksheet)."""

    project_name: str
    id: str = field(default_factory=new_domain_id)
    source_record_id: str | None = None
    sequence: int | None = None
    role: str | None = None
    beneficiary: str | None = None
    donor: str | None = None
    country: str | None = None
    period_text: str | None = None
    working_days: int | None = None
    last_active_year: int | None = None
    description: str | None = None
    responsibilities: str | None = None
    tools_technologies_text: str | None = None
    web_link: str | None = None
    source_document_id: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.project_name = require_non_empty(self.project_name, "project_name")
        self.working_days = _validate_non_negative_days(self.working_days)

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "source_record_id": self.source_record_id,
                "sequence": self.sequence,
                "project_name": self.project_name,
                "role": self.role,
                "beneficiary": self.beneficiary,
                "donor": self.donor,
                "country": self.country,
                "period_text": self.period_text,
                "working_days": self.working_days,
                "last_active_year": self.last_active_year,
                "description": self.description,
                "responsibilities": self.responsibilities,
                "tools_technologies_text": self.tools_technologies_text,
                "web_link": self.web_link,
                "source_document_id": self.source_document_id,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Assignment:
        return cls(
            id=data["id"],
            source_record_id=data.get("source_record_id"),
            sequence=data.get("sequence"),
            project_name=data["project_name"],
            role=data.get("role"),
            beneficiary=data.get("beneficiary"),
            donor=data.get("donor"),
            country=data.get("country"),
            period_text=data.get("period_text"),
            working_days=data.get("working_days"),
            last_active_year=data.get("last_active_year"),
            description=data.get("description"),
            responsibilities=data.get("responsibilities"),
            tools_technologies_text=data.get("tools_technologies_text"),
            web_link=data.get("web_link"),
            source_document_id=data.get("source_document_id"),
        )
