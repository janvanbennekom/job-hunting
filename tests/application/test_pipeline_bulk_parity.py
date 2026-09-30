"""Parity between bulk pipeline assembly and OpportunityPipelineReader."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
from jobhunter.application.review.dtos import OpportunityQueueFilters
from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService
from jobhunter.application.review.opportunity_reads import OpportunityPipelineReader
from jobhunter.application.review.pipeline_bulk import OpportunityPipelineBulkIndex
from jobhunter.application.review.queue_snapshot import OpportunityQueueSnapshot
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

pytestmark = pytest.mark.integration


def _assert_pipeline_parity(session: Session, *, allow_fake: bool) -> None:
    revision_id = ActiveSearchStrategyResolver(session).resolve().revision_id
    reader = OpportunityPipelineReader(session)
    bulk = OpportunityPipelineBulkIndex.load(session, revision_id, allow_fake=allow_fake)
    for opp in OpportunityRepository(session).list_all():
        legacy = reader.load(opp, revision_id, allow_fake=allow_fake)
        assembled = bulk.get(opp.id)
        assert assembled.assessment_state is legacy.assessment_state
        assert (assembled.display_assessment and assembled.display_assessment.id) == (
            legacy.display_assessment and legacy.display_assessment.id
        )
        assert (assembled.display_ranking and assembled.display_ranking.id) == (
            legacy.display_ranking and legacy.display_ranking.id
        )


def test_bulk_pipeline_matches_reader_production(db_session: Session) -> None:
    _assert_pipeline_parity(db_session, allow_fake=False)


def test_bulk_pipeline_matches_reader_allow_fake(db_session: Session) -> None:
    _assert_pipeline_parity(db_session, allow_fake=True)


def test_queue_snapshot_list_queue_matches_filters(db_session: Session) -> None:
    service = OpportunityReviewQueryService(db_session)
    filters = OpportunityQueueFilters(
        allow_fake=False,
        relevance_queue=None,
        hide_dismissed=False,
    )
    snap = service.build_snapshot(filters)
    direct = snap.list_queue(filters)
    via_service = service.list_queue(filters)
    assert [i.opportunity_id for i in direct] == [i.opportunity_id for i in via_service]
    for left, right in zip(direct, via_service, strict=True):
        assert left.dynamic_rank == right.dynamic_rank
        assert left.overall_relevance == right.overall_relevance
        assert left.priority_band == right.priority_band
        assert left.review_disposition == right.review_disposition
