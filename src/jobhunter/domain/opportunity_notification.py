"""Append-only audit of opportunity-level notifications (e.g. HIGH ranking alerts)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.opportunity_notification_enums import (
    OpportunityNotificationChannel,
    OpportunityNotificationStatus,
    OpportunityNotificationType,
)
from jobhunter.domain.serialization import (
    deserialize_datetime,
    enum_to_value,
    prune_none,
    serialize_datetime,
    value_to_enum,
)
from jobhunter.domain.validation import require_timezone_aware


def high_ranking_notification_key(ranking_id: str) -> str:
    """Stable identity for a HIGH alert tied to one ranking row.

    A new append-only ranking row (new id / digest) may produce a new alert even
    when an earlier HIGH state for the same opportunity was already notified.
    """

    return f"high_ranking:{require_non_empty(ranking_id, 'ranking_id')}"


@dataclass(slots=True)
class OpportunityNotification:
    opportunity_id: str
    ranking_id: str
    notification_type: OpportunityNotificationType
    channel: OpportunityNotificationChannel
    status: OpportunityNotificationStatus
    attempted_at: datetime
    notification_key: str
    id: str = field(default_factory=new_domain_id)
    sent_at: datetime | None = None
    error_summary: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.ranking_id = require_non_empty(self.ranking_id, "ranking_id")
        self.notification_key = require_non_empty(
            self.notification_key, "notification_key"
        )
        self.attempted_at = require_timezone_aware(
            self.attempted_at, "attempted_at"
        )
        if self.sent_at is not None:
            self.sent_at = require_timezone_aware(self.sent_at, "sent_at")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "ranking_id": self.ranking_id,
                "notification_type": enum_to_value(self.notification_type),
                "channel": enum_to_value(self.channel),
                "status": enum_to_value(self.status),
                "attempted_at": serialize_datetime(self.attempted_at),
                "sent_at": (
                    serialize_datetime(self.sent_at) if self.sent_at else None
                ),
                "error_summary": self.error_summary,
                "notification_key": self.notification_key,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunityNotification:
        sent = data.get("sent_at")
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            ranking_id=data["ranking_id"],
            notification_type=value_to_enum(
                OpportunityNotificationType, data["notification_type"]
            ),
            channel=value_to_enum(
                OpportunityNotificationChannel, data["channel"]
            ),
            status=value_to_enum(
                OpportunityNotificationStatus, data["status"]
            ),
            attempted_at=deserialize_datetime(data["attempted_at"]),
            sent_at=deserialize_datetime(sent) if sent else None,
            error_summary=data.get("error_summary"),
            notification_key=data["notification_key"],
        )
