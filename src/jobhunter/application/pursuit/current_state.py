"""Derive current pursuit status from append-only events."""

from __future__ import annotations

from jobhunter.domain.opportunity_pursuit import OpportunityPursuitStatusEvent
from jobhunter.domain.pursuit_enums import PursuitStatus


def current_pursuit_status(
    events: list[OpportunityPursuitStatusEvent],
) -> PursuitStatus | None:
    """Latest status by recorded_at descending, then id descending for ties."""
    if not events:
        return None
    ordered = sorted(
        events,
        key=lambda e: (e.recorded_at, e.id),
        reverse=True,
    )
    return ordered[0].status
