"""Phase 17G-2B relevance queue presentation policy tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.application.ranking import OpportunityRankingService
from jobhunter.application.review.dtos import OpportunityQueueFilters
from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService
from jobhunter.domain.assessment_enums import AssessmentStatus, OverallRelevance
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.ranking_enums import PriorityBand
from jobhunter.domain.relevance_queue_enums import RelevanceQueueView as View
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.application.review import HumanReviewService

pytestmark = pytest.mark.integration


def _save_openai_assessment(
    session: Session,
    opportunity_id: str,
    revision_id: str,
    decision_id: str,
    *,
    overall: str = OverallRelevance.STRONG_FIT.value,
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
            prompt_schema_version="profile_assessment_v4",
            model_provider="openai",
            model_name="test-gpt",
            result={
                "overall_relevance": overall,
                "source_data_sufficiency": "ADEQUATE",
                "professional_relevance": {"scope_summary": "x"},
                "service_alignments": [],
                "theme_alignments": [],
                "preference_notes": [],
                "interpreted_eligibility": [],
            },
        )
    )


def _eligible_opp(session: Session, opp_id: str, title: str) -> Opportunity:
    return OpportunityRepository(session).save(
        Opportunity(
            id=opp_id,
            title=title,
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )


def _primary_filters() -> OpportunityQueueFilters:
    return OpportunityQueueFilters(relevance_queue=View.PRIMARY)


def test_default_primary_includes_strong_and_moderate(db_session: Session) -> None:
    strong = _eligible_opp(db_session, "rq-strong", "Strong role")
    moderate = _eligible_opp(db_session, "rq-moderate", "Moderate role")
    weak = _eligible_opp(db_session, "rq-weak", "Weak role")
    elig = EligibilityFilterService(db_session)
    for opp, rel in (
        (strong, OverallRelevance.STRONG_FIT.value),
        (moderate, OverallRelevance.MODERATE_FIT.value),
        (weak, OverallRelevance.WEAK_FIT.value),
    ):
        decision = elig.evaluate_and_persist(opp.id).decision
        _save_openai_assessment(
            db_session,
            opp.id,
            decision.search_strategy_revision_id,
            decision.id,
            overall=rel,
        )
        OpportunityRankingService(db_session).rank_opportunity(opp.id)

    items = OpportunityReviewQueryService(db_session).list_queue(_primary_filters())
    ids = {i.opportunity_id for i in items}
    assert "rq-strong" in ids
    assert "rq-moderate" in ids
    assert "rq-weak" not in ids


def test_primary_excludes_weak_and_out_of_scope(db_session: Session) -> None:
    weak = _eligible_opp(db_session, "rq-w2", "Weak")
    oos = _eligible_opp(db_session, "rq-oos", "OOS")
    elig = EligibilityFilterService(db_session)
    for opp, rel in (
        (weak, OverallRelevance.WEAK_FIT.value),
        (oos, OverallRelevance.OUT_OF_SCOPE.value),
    ):
        d = elig.evaluate_and_persist(opp.id).decision
        _save_openai_assessment(
            db_session, opp.id, d.search_strategy_revision_id, d.id, overall=rel
        )
        OpportunityRankingService(db_session).rank_opportunity(opp.id)

    items = OpportunityReviewQueryService(db_session).list_queue(_primary_filters())
    ids = {i.opportunity_id for i in items}
    assert "rq-w2" not in ids
    assert "rq-oos" not in ids


def test_weak_view_contains_weak_fit(db_session: Session) -> None:
    weak = _eligible_opp(db_session, "rq-w3", "Weak only")
    d = EligibilityFilterService(db_session).evaluate_and_persist(weak.id).decision
    _save_openai_assessment(
        db_session,
        weak.id,
        d.search_strategy_revision_id,
        d.id,
        overall=OverallRelevance.WEAK_FIT.value,
    )
    OpportunityRankingService(db_session).rank_opportunity(weak.id)
    items = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(relevance_queue=View.WEAK)
    )
    assert any(i.opportunity_id == "rq-w3" for i in items)


def test_out_of_scope_view_contains_out_of_scope(db_session: Session) -> None:
    oos = _eligible_opp(db_session, "rq-oos2", "OOS only")
    d = EligibilityFilterService(db_session).evaluate_and_persist(oos.id).decision
    _save_openai_assessment(
        db_session,
        oos.id,
        d.search_strategy_revision_id,
        d.id,
        overall=OverallRelevance.OUT_OF_SCOPE.value,
    )
    OpportunityRankingService(db_session).rank_opportunity(oos.id)
    items = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(relevance_queue=View.OUT_OF_SCOPE)
    )
    assert any(i.opportunity_id == "rq-oos2" for i in items)


def test_unassessed_visible_in_needs_review_segment(db_session: Session) -> None:
    opp = _eligible_opp(db_session, "rq-no-assess", "No assessment")
    EligibilityFilterService(db_session).evaluate_and_persist(opp.id)
    items = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(relevance_queue=View.NEEDS_REVIEW)
    )
    assert any(i.opportunity_id == "rq-no-assess" for i in items)
    primary = OpportunityReviewQueryService(db_session).list_queue(_primary_filters())
    assert not any(i.opportunity_id == "rq-no-assess" for i in primary)


def test_moderate_fit_in_primary_independent_of_ranking_band(
    db_session: Session,
) -> None:
    """Relevance queue must not use ranking band as a gate (LOW != WEAK_FIT)."""
    opp = _eligible_opp(db_session, "rq-low-mod", "Moderate ranked")
    d = EligibilityFilterService(db_session).evaluate_and_persist(opp.id).decision
    _save_openai_assessment(
        db_session,
        opp.id,
        d.search_strategy_revision_id,
        d.id,
        overall=OverallRelevance.MODERATE_FIT.value,
    )
    OpportunityRankingService(db_session).rank_opportunity(opp.id)
    items = OpportunityReviewQueryService(db_session).list_queue(_primary_filters())
    row = next(i for i in items if i.opportunity_id == "rq-low-mod")
    assert row.overall_relevance == OverallRelevance.MODERATE_FIT.value
    assert row.priority_band is not None


def test_high_band_out_of_scope_stays_out_of_scope_view(db_session: Session) -> None:
    opp = _eligible_opp(db_session, "rq-high-oos", "High OOS")
    d = EligibilityFilterService(db_session).evaluate_and_persist(opp.id).decision
    _save_openai_assessment(
        db_session,
        opp.id,
        d.search_strategy_revision_id,
        d.id,
        overall=OverallRelevance.OUT_OF_SCOPE.value,
    )
    OpportunityRankingService(db_session).rank_opportunity(opp.id)
    oos_items = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(relevance_queue=View.OUT_OF_SCOPE)
    )
    row = next(i for i in oos_items if i.opportunity_id == "rq-high-oos")
    assert row.overall_relevance == OverallRelevance.OUT_OF_SCOPE.value
    primary = OpportunityReviewQueryService(db_session).list_queue(_primary_filters())
    assert not any(i.opportunity_id == "rq-high-oos" for i in primary)


def test_hide_dismissed_filters_display_only(db_session: Session) -> None:
    opp = _eligible_opp(db_session, "rq-dismiss", "Dismissed")
    d = EligibilityFilterService(db_session).evaluate_and_persist(opp.id).decision
    _save_openai_assessment(
        db_session,
        opp.id,
        d.search_strategy_revision_id,
        d.id,
        overall=OverallRelevance.STRONG_FIT.value,
    )
    HumanReviewService(db_session).append_review(opp.id, ReviewDisposition.DISMISS)
    hidden = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(
            relevance_queue=View.PRIMARY,
            hide_dismissed=True,
        )
    )
    shown = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(
            relevance_queue=View.PRIMARY,
            hide_dismissed=False,
        )
    )
    assert not any(i.opportunity_id == "rq-dismiss" for i in hidden)
    assert any(i.opportunity_id == "rq-dismiss" for i in shown)


def test_shortlist_not_excluded_by_relevance(db_session: Session) -> None:
    opp = _eligible_opp(db_session, "rq-short", "Shortlisted weak")
    d = EligibilityFilterService(db_session).evaluate_and_persist(opp.id).decision
    _save_openai_assessment(
        db_session,
        opp.id,
        d.search_strategy_revision_id,
        d.id,
        overall=OverallRelevance.WEAK_FIT.value,
    )
    HumanReviewService(db_session).append_review(opp.id, ReviewDisposition.SHORTLIST)
    items = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(relevance_queue=View.WEAK)
    )
    row = next(i for i in items if i.opportunity_id == "rq-short")
    assert row.review_disposition is ReviewDisposition.SHORTLIST


def test_primary_sorts_unreviewed_before_reviewed(db_session: Session) -> None:
    a = _eligible_opp(db_session, "rq-ur", "Unreviewed strong")
    b = _eligible_opp(db_session, "rq-rv", "Reviewed strong")
    elig = EligibilityFilterService(db_session)
    for opp in (a, b):
        d = elig.evaluate_and_persist(opp.id).decision
        _save_openai_assessment(
            db_session,
            opp.id,
            d.search_strategy_revision_id,
            d.id,
            overall=OverallRelevance.STRONG_FIT.value,
        )
        OpportunityRankingService(db_session).rank_opportunity(opp.id)
    HumanReviewService(db_session).append_review(b.id, ReviewDisposition.INVESTIGATE)

    items = OpportunityReviewQueryService(db_session).list_queue(_primary_filters())
    order = [i.opportunity_id for i in items if i.opportunity_id in {a.id, b.id}]
    assert order.index("rq-ur") < order.index("rq-rv")


def test_no_relevance_filter_when_segment_unset(db_session: Session) -> None:
    """Internal queries with relevance_queue=None are not segmented by relevance."""
    weak = _eligible_opp(db_session, "rq-seg-none", "Weak unsegmented")
    d = EligibilityFilterService(db_session).evaluate_and_persist(weak.id).decision
    _save_openai_assessment(
        db_session,
        weak.id,
        d.search_strategy_revision_id,
        d.id,
        overall=OverallRelevance.WEAK_FIT.value,
    )
    OpportunityRankingService(db_session).rank_opportunity(weak.id)
    items = OpportunityReviewQueryService(db_session).list_queue(
        OpportunityQueueFilters(relevance_queue=None)
    )
    assert any(i.opportunity_id == "rq-seg-none" for i in items)
