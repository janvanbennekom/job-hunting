"""Canonical normalized opportunity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from jobhunter.domain.enums import (
    EligibilityStatus,
    LifecycleStatus,
    OpportunityType,
)
from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import (
    deserialize_optional_date,
    enum_to_value,
    prune_none,
    serialize_optional_date,
    value_to_enum,
)


@dataclass(slots=True)
class Opportunity:
    """Normalized JobHunter opportunity (source-agnostic)."""

    title: str
    id: str = field(default_factory=new_domain_id)
    organisation: str | None = None
    location: str | None = None
    description: str | None = None
    publication_date: date | None = None
    deadline: date | None = None
    expected_start_date: date | None = None
    opportunity_type: OpportunityType = OpportunityType.UNKNOWN
    lifecycle_status: LifecycleStatus = LifecycleStatus.NEW
    eligibility_status: EligibilityStatus = EligibilityStatus.UNKNOWN
    canonical_identity_key: str | None = None
    source_status: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.title = require_non_empty(self.title, "title")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "title": self.title,
                "organisation": self.organisation,
                "location": self.location,
                "description": self.description,
                "publication_date": serialize_optional_date(self.publication_date),
                "deadline": serialize_optional_date(self.deadline),
                "expected_start_date": serialize_optional_date(
                    self.expected_start_date
                ),
                "opportunity_type": enum_to_value(self.opportunity_type),
                "lifecycle_status": enum_to_value(self.lifecycle_status),
                "eligibility_status": enum_to_value(self.eligibility_status),
                "canonical_identity_key": self.canonical_identity_key,
                "source_status": self.source_status,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Opportunity:
        return cls(
            id=data["id"],
            title=data["title"],
            organisation=data.get("organisation"),
            location=data.get("location"),
            description=data.get("description"),
            publication_date=deserialize_optional_date(
                data.get("publication_date")
            ),
            deadline=deserialize_optional_date(data.get("deadline")),
            expected_start_date=deserialize_optional_date(
                data.get("expected_start_date")
            ),
            opportunity_type=value_to_enum(
                OpportunityType, data.get("opportunity_type", "UNKNOWN")
            ),
            lifecycle_status=value_to_enum(
                LifecycleStatus, data.get("lifecycle_status", "NEW")
            ),
            eligibility_status=value_to_enum(
                EligibilityStatus, data.get("eligibility_status", "UNKNOWN")
            ),
            canonical_identity_key=data.get("canonical_identity_key"),
            source_status=data.get("source_status"),
        )
