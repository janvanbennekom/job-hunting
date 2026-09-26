"""Mappers for opportunity review records."""

from __future__ import annotations

from jobhunter.domain.opportunity_review_record import OpportunityReviewRecord
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.infrastructure.persistence.models import OpportunityReviewRecordRow


def review_record_to_row(entity: OpportunityReviewRecord) -> OpportunityReviewRecordRow:
    return OpportunityReviewRecordRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        recorded_at=entity.recorded_at,
        disposition=entity.disposition.value,
        notes=entity.notes,
        search_strategy_revision_id=entity.search_strategy_revision_id,
        profile_assessment_id=entity.profile_assessment_id,
        ranking_id=entity.ranking_id,
    )


def review_record_to_domain(row: OpportunityReviewRecordRow) -> OpportunityReviewRecord:
    return OpportunityReviewRecord(
        id=row.id,
        opportunity_id=row.opportunity_id,
        recorded_at=row.recorded_at,
        disposition=ReviewDisposition(row.disposition),
        notes=row.notes,
        search_strategy_revision_id=row.search_strategy_revision_id,
        profile_assessment_id=row.profile_assessment_id,
        ranking_id=row.ranking_id,
    )
