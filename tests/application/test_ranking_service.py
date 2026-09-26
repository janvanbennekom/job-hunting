"""Integration tests for ranking service."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.ranking import OpportunityRankingService
from jobhunter.domain.assessment_enums import AssessmentStatus, OverallRelevance
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.ranking_enums import RankingStatus
from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

pytestmark = pytest.mark.integration


def _save_production_assessment(
    session: Session,
    opportunity_id: str,
    revision_id: str,
    decision_id: str,
) -> None:
    repo = OpportunityProfileAssessmentRepository(session)
    repo.save(
        OpportunityProfileAssessment(
            opportunity_id=opportunity_id,
            search_strategy_revision_id=revision_id,
            eligibility_decision_id=decision_id,
            assessed_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            status=AssessmentStatus.SUCCEEDED,
            input_digest="f" * 64,
            opportunity_content_digest="a" * 64,
            profile_evidence_digest="b" * 64,
            prompt_schema_version="profile_assessment_v1",
            model_provider="openai",
            model_name="test-gpt",
            result={
                "overall_relevance": OverallRelevance.MODERATE_FIT.value,
                "source_data_sufficiency": "ADEQUATE",
                "service_alignments": [],
                "theme_alignments": [],
                "preference_notes": [],
                "interpreted_eligibility": [],
            },
        )
    )


def test_ranking_idempotent(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="rank-opp-001",
            title="Land information system specialist",
            lifecycle_status=LifecycleStatus.NEW,
        )
    )
    elig = EligibilityFilterService(db_session)
    decision = elig.evaluate_and_persist(opp.id).decision
    _save_production_assessment(
        db_session, opp.id, decision.search_strategy_revision_id, decision.id
    )
    service = OpportunityRankingService(db_session)
    first = service.rank_opportunity(opp.id)
    second = service.rank_opportunity(opp.id)
    assert first.ranking.status is RankingStatus.RANKED
    assert second.reused
    assert first.ranking.id == second.ranking.id


def test_fake_assessment_unranked_by_default(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="rank-opp-fake-001",
            title="GIS consultant",
            lifecycle_status=LifecycleStatus.NEW,
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
            opportunity_content_digest="a" * 64,
            profile_evidence_digest="b" * 64,
            prompt_schema_version="profile_assessment_v1",
            model_provider="fake",
            model_name="fake-assessment-v1",
            result={"overall_relevance": OverallRelevance.STRONG_FIT.value},
        )
    )
    outcome = OpportunityRankingService(db_session).rank_opportunity(opp.id)
    assert outcome.ranking.status is RankingStatus.UNRANKED
