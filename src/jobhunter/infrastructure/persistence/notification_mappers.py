"""Mappers for opportunity notification audit."""

from __future__ import annotations

from jobhunter.domain.opportunity_notification import OpportunityNotification
from jobhunter.domain.opportunity_notification_enums import (
    OpportunityNotificationChannel,
    OpportunityNotificationStatus,
    OpportunityNotificationType,
)
from jobhunter.infrastructure.persistence.models import OpportunityNotificationRow


def opportunity_notification_to_row(
    entity: OpportunityNotification,
) -> OpportunityNotificationRow:
    return OpportunityNotificationRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        ranking_id=entity.ranking_id,
        notification_type=entity.notification_type.value,
        channel=entity.channel.value,
        status=entity.status.value,
        attempted_at=entity.attempted_at,
        sent_at=entity.sent_at,
        error_summary=entity.error_summary,
        notification_key=entity.notification_key,
    )


def opportunity_notification_to_domain(
    row: OpportunityNotificationRow,
) -> OpportunityNotification:
    return OpportunityNotification(
        id=row.id,
        opportunity_id=row.opportunity_id,
        ranking_id=row.ranking_id,
        notification_type=OpportunityNotificationType(row.notification_type),
        channel=OpportunityNotificationChannel(row.channel),
        status=OpportunityNotificationStatus(row.status),
        attempted_at=row.attempted_at,
        sent_at=row.sent_at,
        error_summary=row.error_summary,
        notification_key=row.notification_key,
    )
