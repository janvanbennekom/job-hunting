"""Configured external opportunity source (not a scan run)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import prune_none


@dataclass(slots=True)
class JobSource:
    """Identity and configuration of an external opportunity source."""

    name: str
    id: str = field(default_factory=new_domain_id)
    organisation: str | None = None
    url: str | None = None
    is_active: bool = True

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "name")
        self.id = require_non_empty(self.id, "id")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "name": self.name,
                "organisation": self.organisation,
                "url": self.url,
                "is_active": self.is_active,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> JobSource:
        return cls(
            id=data["id"],
            name=data["name"],
            organisation=data.get("organisation"),
            url=data.get("url"),
            is_active=data.get("is_active", True),
        )
