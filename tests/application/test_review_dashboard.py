"""Phase 10 dashboard application service tests."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.application.ranking import OpportunityRankingService
from jobhunter.application.review import (
    DashboardSummaryService,
    HumanReviewService,
    OpportunityDetailService,
    OpportunityReviewQueryService,
)
from jobhunter.application.review.dtos import AssessmentDisplayState, OpportunityQueueFilters
from jobhunter.domain.assessment_enums import AssessmentStatus, OverallRelevance
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.opportunity_source import OpportunitySource
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.repositories import (
    OpportunityRepository,
    OpportunitySourceRepository,
)
from jobhunter.infrastructure.persistence.source_scan_repository import SourceScanRepository
from jobhunter.domain.source_scan import SourceScan
from jobhunter.domain.source_scan_enums import SourceScanStatus

pytestmark = pytest.mark.integration


def _save_openai_assessment(
    session: Session,
    opportunity_id: str,
    revision_id: str,
    decision_id: str,
    *,
    overall: str = OverallRelevance.STRONG_FIT.value,
    sufficiency: str = "ADEQUATE",
) -> None:
    OpportunityProfileAssessmentRepository(session).save(
        OpportunityProfileAssessment(
            opportunity_id=opportunity_id,
            search_strategy_revision_id=revision_id,
            eligibility_decision_id=decision_id,
            assessed_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            status=AssessmentStatus.SUCCEEDED,
            input_digest="a" * 64,
            opportunity_content_digest="b" * 64,
            profile_evidence_digest="c" * 64,
            prompt_schema_version="profile_assessment_v1",
            model_provider="openai",
            model_name="test-gpt",
            result={
                "overall_relevance": overall,
                "source_data_sufficiency": sufficiency,
                "professional_relevance": {
                    "scope_summary": "Test scope",
                    "delivery_mode_inference": "onsite",
                    "seniority_inference": "senior",
                    "domain_tags": [],
                },
                "service_alignments": [],
                "theme_alignments": [],
                "preference_notes": [],
                "interpreted_eligibility": [],
            },
        )
    )


def test_queue_excludes_fake_by_default(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="rev-fake-001",
            title="Fake assessed role",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    decision = EligibilityFilterService(db_session).evaluate_and_persist(opp.id).decision
    OpportunityProfileAssessmentRepository(db_session).save(
        OpportunityProfileAssessment(
            opportunity_id=opp.id,
            search_strategy_revision_id=decision.search_strategy_revision_id,
            eligibility_decision_id=decision.id,
            assessed_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            status=AssessmentStatus.SUCCEEDED,
            input_digest="z" * 64,
            opportunity_content_digest="b" * 64,
            profile_evidence_digest="c" * 64,
            prompt_schema_version="profile_assessment_v1",
            model_provider="fake",
            model_name="fake-v1",
            result={"overall_relevance": OverallRelevance.STRONG_FIT.value},
        )
    )
    OpportunityRankingService(db_session).rank_opportunity(
        opp.id, include_fake_assessments=True
    )
    items = OpportunityReviewQueryService(db_session).list_queue()
    row = next((i for i in items if i.opportunity_id == opp.id), None)
    assert row is not None
    assert row.assessment_state is AssessmentDisplayState.FAKE_ONLY
    assert row.dynamic_rank is None

    dev_items = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(allow_fake=True)
    )
    dev_row = next(i for i in dev_items if i.opportunity_id == opp.id)
    assert dev_row.assessment_state is AssessmentDisplayState.FAKE_DEV
    assert dev_row.dynamic_rank is not None


def test_dynamic_rank_ordering(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    high = opportunities.save(
        Opportunity(
            id="rev-rank-high",
            title="High band role",
            lifecycle_status=LifecycleStatus.NEW,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    low = opportunities.save(
        Opportunity(
            id="rev-rank-low",
            title="Low band role",
            lifecycle_status=LifecycleStatus.NEW,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    elig = EligibilityFilterService(db_session)
    d_high = elig.evaluate_and_persist(high.id).decision
    d_low = elig.evaluate_and_persist(low.id).decision
    _save_openai_assessment(
        db_session, high.id, d_high.search_strategy_revision_id, d_high.id
    )
    _save_openai_assessment(
        db_session,
        low.id,
        d_low.search_strategy_revision_id,
        d_low.id,
        overall=OverallRelevance.WEAK_FIT.value,
    )
    ranking = OpportunityRankingService(db_session)
    ranking.rank_opportunity(high.id)
    ranking.rank_opportunity(low.id)

    items = OpportunityReviewQueryService(db_session).list_queue()
    ranked = [i for i in items if i.opportunity_id in {high.id, low.id}]
    assert len(ranked) == 2
    high_row = next(i for i in ranked if i.opportunity_id == high.id)
    low_row = next(i for i in ranked if i.opportunity_id == low.id)
    assert high_row.priority_band is PriorityBand.HIGH
    assert high_row.dynamic_rank is not None
    assert low_row.dynamic_rank is not None
    assert high_row.dynamic_rank < low_row.dynamic_rank


def test_default_queue_eligible_only(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opportunities.save(
        Opportunity(
            id="rev-inelig-001",
            title="Internship",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.INELIGIBLE,
        )
    )
    items = OpportunityReviewQueryService(db_session).list_queue()
    assert all(i.eligibility_status is EligibilityStatus.ELIGIBLE for i in items)


def test_detail_partial_states(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="rev-detail-001",
            title="Closed role",
            lifecycle_status=LifecycleStatus.CLOSED,
            eligibility_status=EligibilityStatus.INELIGIBLE,
        )
    )
    detail = OpportunityDetailService(db_session).get_detail(opp.id)
    assert detail is not None
    assert detail.assessment.present is False
    assert detail.ranking.explanation is not None


def test_human_review_append_only(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="rev-review-001",
            title="Review me",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    service = HumanReviewService(db_session)
    first = service.append_review(opp.id, ReviewDisposition.INVESTIGATE, "note 1")
    second = service.append_review(opp.id, ReviewDisposition.SHORTLIST, "note 2")
    assert first.id != second.id
    latest = service.get_latest(opp.id)
    assert latest is not None
    assert latest.disposition is ReviewDisposition.SHORTLIST
    history = service.list_history(opp.id)
    assert len(history) == 2


def test_dashboard_summary_and_scan(db_session: Session) -> None:
    SourceScanRepository(db_session).save(
        SourceScan(
            id="scan-test-001",
            source_id="fao-external-jobs",
            started_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            completed_at=datetime(2026, 6, 1, 1, tzinfo=timezone.utc),
            status=SourceScanStatus.SUCCESS,
            records_retrieved=3,
        )
    )
    summary = DashboardSummaryService(db_session).build_summary()
    assert summary.latest_scan is not None
    assert summary.latest_scan.status == "SUCCESS"


def test_source_link_on_detail(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="rev-link-001",
            title="Linked role",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
        )
    )
    OpportunitySourceRepository(db_session).save(
        OpportunitySource(
            opportunity_id=opp.id,
            source_id="fao-external-jobs",
            source_url="https://example.com/list",
            original_url="https://example.com/job/99",
            last_seen_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
    )
    detail = OpportunityDetailService(db_session).get_detail(opp.id)
    assert detail is not None
    assert detail.facts.primary_external_url == "https://example.com/list"
    assert detail.facts.application_url == "https://example.com/job/99"


def test_list_summary_only_sufficiency(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="rev-suff-001",
            title="Summary only",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    decision = EligibilityFilterService(db_session).evaluate_and_persist(opp.id).decision
    _save_openai_assessment(
        db_session,
        opp.id,
        decision.search_strategy_revision_id,
        decision.id,
        sufficiency="LIST_SUMMARY_ONLY",
    )
    items = OpportunityReviewQueryService(db_session).list_queue()
    row = next(i for i in items if i.opportunity_id == opp.id)
    assert row.source_data_sufficiency == "LIST_SUMMARY_ONLY"
