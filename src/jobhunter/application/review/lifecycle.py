"""Lifecycle helpers for dashboard filtering."""

from __future__ import annotations

from jobhunter.domain.enums import LifecycleStatus

ACTIONABLE_LIFECYCLE_STATUSES = frozenset(
    {
        LifecycleStatus.NEW,
        LifecycleStatus.UPDATED,
        LifecycleStatus.STILL_OPEN,
    }
)


def is_actionable_lifecycle(status: LifecycleStatus) -> bool:
    return status in ACTIONABLE_LIFECYCLE_STATUSES
