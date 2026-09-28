"""Pursuit tracking application service."""

from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from jobhunter.application.pursuit import PursuitOperationalUpdate, PursuitTrackingService
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus, OpportunityType
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.pursuit_enums import PursuitStatus
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository


def _save_opp(session, opp_id: str = "opp-pursuit-1") -> str:
    repo = OpportunityRepository(session)
    repo.save(
        Opportunity(
            id=opp_id,
            title="Land administration GIS specialist",
            organisation="Test client",
            lifecycle_status=LifecycleStatus.NEW,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            opportunity_type=OpportunityType.CONSULTANCY,
        )
    )
    return opp_id


@pytest.mark.integration
def test_start_pursuit_and_transition(db_session) -> None:
    oid = _save_opp(db_session)
    svc = PursuitTrackingService(db_session)
    view = svc.start_pursuit(oid, notes="Initial interest")
    assert view.current_status is PursuitStatus.CONSIDERING
    assert view.opportunity_id == oid

    view = svc.record_status_transition(
        oid, PursuitStatus.SUBMITTED, notes="EOI sent"
    )
    assert view.current_status is PursuitStatus.SUBMITTED
    assert len(view.history) == 2


@pytest.mark.integration
def test_terminal_and_duplicate_start(db_session) -> None:
    oid = _save_opp(db_session, "opp-pursuit-2")
    svc = PursuitTrackingService(db_session)
    svc.start_pursuit(oid)
    svc.record_status_transition(oid, PursuitStatus.WITHDRAWN)
    with pytest.raises(ValueError, match="terminal"):
        svc.record_status_transition(oid, PursuitStatus.PREPARING)
    with pytest.raises(ValueError, match="already exists"):
        svc.start_pursuit(oid)


@pytest.mark.integration
def test_operational_update_and_queries(db_session) -> None:
    oid = _save_opp(db_session, "opp-pursuit-3")
    svc = PursuitTrackingService(db_session)
    svc.start_pursuit(oid)
    svc.update_operational(
        oid,
        PursuitOperationalUpdate(
            next_action="Prepare TOR response",
            next_action_date=date(2026, 10, 1),
            submission_deadline=date(2026, 10, 15),
        ),
    )
    view = svc.get_current(oid)
    assert view is not None
    assert view.next_action == "Prepare TOR response"
    assert view.submission_deadline == date(2026, 10, 15)


@pytest.mark.integration
def test_shortlist_does_not_auto_start_pursuit(db_session) -> None:
    """Review triage does not create pursuit records (explicit start only)."""
    oid = _save_opp(db_session, "opp-pursuit-4")
    assert PursuitTrackingService(db_session).get_current(oid) is None


@pytest.mark.integration
def test_no_pursuit_by_default(db_session) -> None:
    oid = _save_opp(db_session, "opp-pursuit-5")
    assert PursuitTrackingService(db_session).get_current(oid) is None
