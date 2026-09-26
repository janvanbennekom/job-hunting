"""Repositories for human review records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.opportunity_review_record import OpportunityReviewRecord
from jobhunter.infrastructure.persistence import review_mappers as mappers
from jobhunter.infrastructure.persistence.models import OpportunityReviewRecordRow


class OpportunityReviewRecordRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunityReviewRecord) -> OpportunityReviewRecord:
        row = mappers.review_record_to_row(entity)
        self._session.add(row)
        self._session.flush()
        return mappers.review_record_to_domain(row)

    def list_for_opportunity(
        self, opportunity_id: str
    ) -> list[OpportunityReviewRecord]:
        stmt = (
            select(OpportunityReviewRecordRow)
            .where(OpportunityReviewRecordRow.opportunity_id == opportunity_id)
            .order_by(OpportunityReviewRecordRow.recorded_at.desc())
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.review_record_to_domain(row) for row in rows]

    def get_latest_for_opportunity(
        self, opportunity_id: str
    ) -> OpportunityReviewRecord | None:
        stmt = (
            select(OpportunityReviewRecordRow)
            .where(OpportunityReviewRecordRow.opportunity_id == opportunity_id)
            .order_by(OpportunityReviewRecordRow.recorded_at.desc())
            .limit(1)
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.review_record_to_domain(row)

    def map_latest_by_opportunity_ids(
        self, opportunity_ids: list[str]
    ) -> dict[str, OpportunityReviewRecord]:
        if not opportunity_ids:
            return {}
        stmt = (
            select(OpportunityReviewRecordRow)
            .where(OpportunityReviewRecordRow.opportunity_id.in_(opportunity_ids))
            .order_by(
                OpportunityReviewRecordRow.opportunity_id,
                OpportunityReviewRecordRow.recorded_at.desc(),
            )
        )
        rows = self._session.scalars(stmt).all()
        result: dict[str, OpportunityReviewRecord] = {}
        for row in rows:
            if row.opportunity_id in result:
                continue
            result[row.opportunity_id] = mappers.review_record_to_domain(row)
        return result
