"""Pursuit status transition validation."""

from __future__ import annotations

from jobhunter.domain.pursuit_enums import (
    TERMINAL_PURSUIT_STATUSES,
    PursuitStatus,
)


def validate_pursuit_transition(
    current: PursuitStatus | None,
    new_status: PursuitStatus,
) -> None:
    """Raise ValueError when a transition is not allowed.

    Stage skipping is allowed (e.g. CONSIDERING → SUBMITTED). Terminal states
    cannot transition further without reopening pursuit (separate operation).
    """
    if current is None:
        if new_status is not PursuitStatus.CONSIDERING:
            raise ValueError(
                "Initial pursuit status must be CONSIDERING when starting tracking."
            )
        return
    if current in TERMINAL_PURSUIT_STATUSES:
        raise ValueError(
            f"Cannot transition from terminal pursuit status {current.value}."
        )
    if new_status == current:
        raise ValueError(
            f"Pursuit status is already {current.value}; record notes via "
            "operational update or choose a different status."
        )
