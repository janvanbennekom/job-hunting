"""HIGH ranking opportunity alert policy and idempotency tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.automation.high_ranking_alerts import (
    HighRankingAlertService,
    HighRankingOpportunityAlert,
    ranking_eligible_for_high_alert,
)
from jobhunter.application.ranking.service import RankingOutcome
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus, OpportunityType
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_notification import high_ranking_notification_key
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.assessment_enums import AssessmentStatus
from jobhunter.domain.opportunity_ranking import OpportunityRanking
from jobhunter.domain.ranking_enums import FactorEffect, PriorityBand, RankingStatus
from jobhunter.domain.ranking_factor import RankingFactor
from jobhunter.infrastructure.config import Settings
from jobhunter.infrastructure.persistence.opportunity_notification_repository import (
    OpportunityNotificationRepository,
)
from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.ranking_repositories import (
    OpportunityRankingRepository,
)


class _RecordingSender:
    def __init__(self) -> None:
        self.summaries: list = []
        self.alerts: list[HighRankingOpportunityAlert] = []

    def send(self, summary) -> None:
        self.summaries.append(summary)

    def send_high_ranking_alert(self, alert: object) -> None:
        assert isinstance(alert, HighRankingOpportunityAlert)
        self.alerts.append(alert)


def _settings() -> Settings:
    return Settings(
        env="test",
        log_level="INFO",
        database_url="postgresql://unused",
        openai_api_key=None,
        openai_model=None,
    )


def test_policy_rejects_medium_low_ineligible_closed_fake() -> None:
    base = {
        "lifecycle_status": LifecycleStatus.NEW,
        "eligibility_status": EligibilityStatus.ELIGIBLE,
        "ranking_status": RankingStatus.RANKED,
        "priority_band": PriorityBand.HIGH,
        "assessment_provider": "openai",
    }
    assert ranking_eligible_for_high_alert(**base)
    assert not ranking_eligible_for_high_alert(
        **{**base, "priority_band": PriorityBand.MEDIUM}
    )
    assert not ranking_eligible_for_high_alert(
        **{**base, "priority_band": PriorityBand.LOW}
    )
    assert not ranking_eligible_for_high_alert(
        **{**base, "ranking_status": RankingStatus.UNRANKED}
    )
    assert not ranking_eligible_for_high_alert(
        **{**base, "eligibility_status": EligibilityStatus.INELIGIBLE}
    )
    assert not ranking_eligible_for_high_alert(
        **{**base, "lifecycle_status": LifecycleStatus.CLOSED}
    )
    assert not ranking_eligible_for_high_alert(
        **{**base, "lifecycle_status": LifecycleStatus.EXPIRED}
    )
    assert not ranking_eligible_for_high_alert(
        **{**base, "assessment_provider": "fake"}
    )


def _save_high_ranking(
    db_session: Session,
    *,
    title: str,
    ranking_input_digest: str,
) -> tuple[Opportunity, OpportunityRanking]:
    opp_repo = OpportunityRepository(db_session)
    rank_repo = OpportunityRankingRepository(db_session)
    assess_repo = OpportunityProfileAssessmentRepository(db_session)
    opp = opp_repo.save(
        Opportunity(
            title=title,
            opportunity_type=OpportunityType.CONSULTANCY,
            lifecycle_status=LifecycleStatus.NEW,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    decision = EligibilityFilterService(db_session).evaluate_and_persist(opp.id).decision
    revision_id = decision.search_strategy_revision_id
    assessment = assess_repo.save(
        OpportunityProfileAssessment(
            opportunity_id=opp.id,
            search_strategy_revision_id=revision_id,
            eligibility_decision_id=decision.id,
            assessed_at=datetime.now(timezone.utc),
            status=AssessmentStatus.SUCCEEDED,
            input_digest="f" * 64,
            opportunity_content_digest="oc" * 32,
            profile_evidence_digest="pe" * 32,
            prompt_schema_version="profile_assessment_v1",
            model_provider="openai",
            model_name="gpt-test",
            result={"strengths": ["GIS implementation"]},
        )
    )
    ranking = rank_repo.save(
        OpportunityRanking(
            opportunity_id=opp.id,
            search_strategy_revision_id=revision_id,
            ranked_at=datetime.now(timezone.utc),
            status=RankingStatus.RANKED,
            priority_band=PriorityBand.HIGH,
            input_digest=ranking_input_digest,
            ranking_method_version="ranking_v1",
            ranking_config_hash="cfg",
            profile_assessment_id=assessment.id,
            factors=[
                RankingFactor(
                    code="DOMAIN",
                    effect=FactorEffect.INCREASED,
                    summary="Strong LIS alignment",
                )
            ],
        )
    )
    return opp, ranking


@pytest.mark.integration
def test_high_alert_sent_once_then_suppressed(db_session: Session) -> None:
    _, ranking = _save_high_ranking(
        db_session,
        title="Land Information System Expert",
        ranking_input_digest="a" * 64,
    )
    sender = _RecordingSender()
    service = HighRankingAlertService(db_session, _settings())
    outcome = RankingOutcome(ranking=ranking, reused=False)
    first = service.process_ranking_outcomes([outcome], sender=sender)
    second = service.process_ranking_outcomes([outcome], sender=sender)
    assert first.sent == 1
    assert len(sender.alerts) == 1
    assert second.sent == 0
    assert second.skipped >= 1
    key = high_ranking_notification_key(ranking.id)
    assert OpportunityNotificationRepository(db_session).has_successful_delivery(key)


@pytest.mark.integration
def test_new_ranking_row_can_alert_again(db_session: Session) -> None:
    opp, ranking1 = _save_high_ranking(
        db_session, title="GIS Advisor", ranking_input_digest="b" * 64,
    )
    rank_repo = OpportunityRankingRepository(db_session)
    assess_repo = OpportunityProfileAssessmentRepository(db_session)
    assessment = assess_repo.list_for_opportunity(opp.id)[-1]
    sender = _RecordingSender()
    service = HighRankingAlertService(db_session, _settings())
    service.process_ranking_outcomes(
        [RankingOutcome(ranking=ranking1, reused=False)], sender=sender
    )
    ranking2 = rank_repo.save(
        OpportunityRanking(
            opportunity_id=opp.id,
            search_strategy_revision_id=ranking1.search_strategy_revision_id,
            ranked_at=datetime.now(timezone.utc),
            status=RankingStatus.RANKED,
            priority_band=PriorityBand.HIGH,
            input_digest="c" * 64,
            ranking_method_version="ranking_v1",
            ranking_config_hash="cfg",
            profile_assessment_id=assessment.id,
        )
    )
    result = service.process_ranking_outcomes(
        [RankingOutcome(ranking=ranking2, reused=False)], sender=sender
    )
    assert result.sent == 1
    assert len(sender.alerts) == 2


class _FailingSender(_RecordingSender):
    def send_high_ranking_alert(self, alert: object) -> None:
        raise RuntimeError("smtp down")


@pytest.mark.integration
def test_failed_send_recorded_and_retry_succeeds(db_session: Session) -> None:
    _, ranking = _save_high_ranking(
        db_session, title="Cadastre Specialist", ranking_input_digest="d" * 64,
    )
    failing = _FailingSender()
    service = HighRankingAlertService(db_session, _settings())
    fail_result = service.process_ranking_outcomes(
        [RankingOutcome(ranking=ranking, reused=False)], sender=failing
    )
    assert fail_result.failed == 1
    key = high_ranking_notification_key(ranking.id)
    repo = OpportunityNotificationRepository(db_session)
    assert not repo.has_successful_delivery(key)
    record = repo.get_by_key(key)
    assert record is not None
    assert record.error_summary

    ok_sender = _RecordingSender()
    ok_result = service.process_ranking_outcomes(
        [RankingOutcome(ranking=ranking, reused=False)], sender=ok_sender
    )
    assert ok_result.sent == 1
    assert repo.has_successful_delivery(key)


def test_reused_ranking_outcome_skipped() -> None:
    ranking = OpportunityRanking(
        opportunity_id="opp-1",
        search_strategy_revision_id="rev-1",
        ranked_at=datetime.now(timezone.utc),
        status=RankingStatus.RANKED,
        priority_band=PriorityBand.HIGH,
        input_digest="e" * 64,
        ranking_method_version="ranking_v1",
        ranking_config_hash="cfg",
    )
    sender = _RecordingSender()
    service = HighRankingAlertService(MagicMock(), _settings())
    result = service.process_ranking_outcomes(
        [RankingOutcome(ranking=ranking, reused=True)], sender=sender
    )
    assert result.skipped == 1
    assert result.sent == 0
    assert len(sender.alerts) == 0
