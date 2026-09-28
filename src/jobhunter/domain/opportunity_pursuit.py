"""Opportunity pursuit (application) tracking — Phase 14."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.pursuit_enums import PursuitStatus
from jobhunter.domain.serialization import (
    deserialize_date,
    deserialize_datetime,
    enum_to_value,
    prune_none,
    serialize_date,
    serialize_datetime,
    value_to_enum,
)
from jobhunter.domain.validation import require_timezone_aware


@dataclass(slots=True)
class OpportunityPursuit:
    """One active pursuit thread per opportunity (created by explicit human action)."""

    opportunity_id: str
    started_at: datetime
    id: str = field(default_factory=new_domain_id)
    submission_deadline: date | None = None
    submission_url: str | None = None
    next_action: str | None = None
    next_action_date: date | None = None
    contact_name: str | None = None
    contact_organisation: str | None = None
    contact_email: str | None = None
    reference_identifier: str | None = None
    operational_updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.started_at = require_timezone_aware(self.started_at, "started_at")
        if self.operational_updated_at is not None:
            self.operational_updated_at = require_timezone_aware(
                self.operational_updated_at, "operational_updated_at"
            )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "started_at": serialize_datetime(self.started_at),
                "submission_deadline": (
                    serialize_date(self.submission_deadline)
                    if self.submission_deadline
                    else None
                ),
                "submission_url": self.submission_url,
                "next_action": self.next_action,
                "next_action_date": (
                    serialize_date(self.next_action_date)
                    if self.next_action_date
                    else None
                ),
                "contact_name": self.contact_name,
                "contact_organisation": self.contact_organisation,
                "contact_email": self.contact_email,
                "reference_identifier": self.reference_identifier,
                "operational_updated_at": (
                    serialize_datetime(self.operational_updated_at)
                    if self.operational_updated_at
                    else None
                ),
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunityPursuit:
        sd = data.get("submission_deadline")
        nad = data.get("next_action_date")
        ou = data.get("operational_updated_at")
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            started_at=deserialize_datetime(data["started_at"]),
            submission_deadline=deserialize_date(sd) if sd else None,
            submission_url=data.get("submission_url"),
            next_action=data.get("next_action"),
            next_action_date=deserialize_date(nad) if nad else None,
            contact_name=data.get("contact_name"),
            contact_organisation=data.get("contact_organisation"),
            contact_email=data.get("contact_email"),
            reference_identifier=data.get("reference_identifier"),
            operational_updated_at=deserialize_datetime(ou) if ou else None,
        )


@dataclass(slots=True)
class OpportunityPursuitStatusEvent:
    """Append-only pursuit status transition."""

    pursuit_id: str
    opportunity_id: str
    recorded_at: datetime
    status: PursuitStatus
    id: str = field(default_factory=new_domain_id)
    notes: str | None = None
    effective_date: date | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.pursuit_id = require_non_empty(self.pursuit_id, "pursuit_id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.recorded_at = require_timezone_aware(
            self.recorded_at, "recorded_at"
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "pursuit_id": self.pursuit_id,
                "opportunity_id": self.opportunity_id,
                "recorded_at": serialize_datetime(self.recorded_at),
                "status": enum_to_value(self.status),
                "notes": self.notes,
                "effective_date": (
                    serialize_date(self.effective_date)
                    if self.effective_date
                    else None
                ),
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunityPursuitStatusEvent:
        ed = data.get("effective_date")
        return cls(
            id=data["id"],
            pursuit_id=data["pursuit_id"],
            opportunity_id=data["opportunity_id"],
            recorded_at=deserialize_datetime(data["recorded_at"]),
            status=value_to_enum(PursuitStatus, data["status"]),
            notes=data.get("notes"),
            effective_date=deserialize_date(ed) if ed else None,
        )
