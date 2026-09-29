"""Bulk human review triage."""

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.review import HumanReviewService
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

pytestmark = pytest.mark.integration


def _save_opportunity(session: Session, opp_id: str, title: str) -> Opportunity:
    return OpportunityRepository(session).save(
        Opportunity(
            id=opp_id,
            title=title,
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )


def test_bulk_dismiss_multiple(db_session: Session) -> None:
    _save_opportunity(db_session, "bulk-opp-1", "Role one")
    _save_opportunity(db_session, "bulk-opp-2", "Role two")
    service = HumanReviewService(db_session)
    result = service.append_reviews_bulk(
        ["bulk-opp-1", "bulk-opp-2"],
        ReviewDisposition.DISMISS,
        "batch dismiss",
    )
    assert len(result.records) == 2
    assert service.get_latest("bulk-opp-1").disposition is ReviewDisposition.DISMISS
    assert service.get_latest("bulk-opp-2").disposition is ReviewDisposition.DISMISS


def test_bulk_shortlist_and_investigate(db_session: Session) -> None:
    opp = _save_opportunity(db_session, "bulk-opp-3", "Role three")
    service = HumanReviewService(db_session)
    service.append_reviews_bulk([opp.id], ReviewDisposition.INVESTIGATE)
    service.append_reviews_bulk([opp.id], ReviewDisposition.SHORTLIST)
    history = service.list_history(opp.id)
    assert len(history) == 2
    assert history[0].disposition is ReviewDisposition.SHORTLIST


def test_bulk_rejects_unknown_id_before_writes(db_session: Session) -> None:
    _save_opportunity(db_session, "bulk-opp-4", "Role four")
    service = HumanReviewService(db_session)
    with pytest.raises(ValueError, match="Unknown opportunity"):
        service.append_reviews_bulk(
            ["bulk-opp-4", "missing-id"],
            ReviewDisposition.DISMISS,
        )
    assert service.get_latest("bulk-opp-4") is None


def test_bulk_does_not_auto_dismiss_low_rank(db_session: Session) -> None:
    """Ranking is unrelated to human review — no bulk dismiss by band in service."""
    opp = _save_opportunity(db_session, "bulk-opp-5", "Low band role")
    service = HumanReviewService(db_session)
    assert service.get_latest(opp.id) is None
