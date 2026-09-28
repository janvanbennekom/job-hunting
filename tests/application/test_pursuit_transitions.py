"""Pursuit transition rules and current-state derivation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from jobhunter.application.pursuit.current_state import current_pursuit_status
from jobhunter.application.pursuit.transitions import validate_pursuit_transition
from jobhunter.domain.opportunity_pursuit import OpportunityPursuitStatusEvent
from jobhunter.domain.pursuit_enums import PursuitStatus


def test_initial_must_be_considering() -> None:
    validate_pursuit_transition(None, PursuitStatus.CONSIDERING)
    with pytest.raises(ValueError, match="Initial"):
        validate_pursuit_transition(None, PursuitStatus.SUBMITTED)


def test_stage_skipping_allowed() -> None:
    validate_pursuit_transition(
        PursuitStatus.CONSIDERING, PursuitStatus.SUBMITTED
    )


def test_terminal_blocks_further_transitions() -> None:
    with pytest.raises(ValueError, match="terminal"):
        validate_pursuit_transition(PursuitStatus.AWARDED, PursuitStatus.PREPARING)


def test_same_status_rejected() -> None:
    with pytest.raises(ValueError, match="already"):
        validate_pursuit_transition(PursuitStatus.PREPARING, PursuitStatus.PREPARING)


def test_current_status_latest_recorded_at() -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [
        OpportunityPursuitStatusEvent(
            pursuit_id="p1",
            opportunity_id="o1",
            recorded_at=base,
            status=PursuitStatus.CONSIDERING,
            id="e1",
        ),
        OpportunityPursuitStatusEvent(
            pursuit_id="p1",
            opportunity_id="o1",
            recorded_at=base.replace(hour=1),
            status=PursuitStatus.SUBMITTED,
            id="e2",
        ),
    ]
    assert current_pursuit_status(events) is PursuitStatus.SUBMITTED
