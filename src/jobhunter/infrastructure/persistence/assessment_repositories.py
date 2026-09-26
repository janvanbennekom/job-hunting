"""Repositories for opportunity profile assessments."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.assessment_enums import AssessmentStatus
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.infrastructure.persistence import assessment_mappers as mappers
from jobhunter.infrastructure.persistence.models import OpportunityProfileAssessmentRow

_SUCCESS_STATUSES = (
    AssessmentStatus.SUCCEEDED.value,
    AssessmentStatus.SUCCEEDED_WITH_WARNINGS.value,
)


class OpportunityProfileAssessmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunityProfileAssessment) -> OpportunityProfileAssessment:
        row = mappers.assessment_to_row(entity)
        self._session.add(row)
        self._session.flush()
        return mappers.assessment_to_domain(row)

    def get_by_id(self, entity_id: str) -> OpportunityProfileAssessment | None:
        row = self._session.get(OpportunityProfileAssessmentRow, entity_id)
        if row is None:
            return None
        return mappers.assessment_to_domain(row)

    def list_for_opportunity(
        self, opportunity_id: str
    ) -> list[OpportunityProfileAssessment]:
        stmt = (
            select(OpportunityProfileAssessmentRow)
            .where(OpportunityProfileAssessmentRow.opportunity_id == opportunity_id)
            .order_by(OpportunityProfileAssessmentRow.assessed_at)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.assessment_to_domain(row) for row in rows]

    def find_reusable_success(
        self, opportunity_id: str, input_digest: str
    ) -> OpportunityProfileAssessment | None:
        stmt = (
            select(OpportunityProfileAssessmentRow)
            .where(
                OpportunityProfileAssessmentRow.opportunity_id == opportunity_id,
                OpportunityProfileAssessmentRow.input_digest == input_digest,
                OpportunityProfileAssessmentRow.status.in_(_SUCCESS_STATUSES),
            )
            .order_by(OpportunityProfileAssessmentRow.assessed_at.desc())
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.assessment_to_domain(row)
