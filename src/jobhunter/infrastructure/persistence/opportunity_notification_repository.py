"""Persistence for opportunity notification audit rows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.opportunity_notification import OpportunityNotification
from jobhunter.domain.opportunity_notification_enums import (
    OpportunityNotificationStatus,
)
from jobhunter.infrastructure.persistence import notification_mappers as mappers
from jobhunter.infrastructure.persistence.models import OpportunityNotificationRow


class OpportunityNotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunityNotification) -> OpportunityNotification:
        row = mappers.opportunity_notification_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.opportunity_notification_to_domain(merged)

    def get_by_key(self, notification_key: str) -> OpportunityNotification | None:
        stmt = select(OpportunityNotificationRow).where(
            OpportunityNotificationRow.notification_key == notification_key
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.opportunity_notification_to_domain(row)

    def has_successful_delivery(self, notification_key: str) -> bool:
        stmt = select(OpportunityNotificationRow.id).where(
            OpportunityNotificationRow.notification_key == notification_key,
            OpportunityNotificationRow.status
            == OpportunityNotificationStatus.SENT.value,
        )
        return self._session.scalars(stmt).first() is not None
