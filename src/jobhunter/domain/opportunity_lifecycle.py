"""Lifecycle status rules for opportunity processing."""

from __future__ import annotations

from datetime import date

from jobhunter.domain.enums import LifecycleStatus
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity


_CLOSED_STATUSES = frozenset(
    {"closed", "cancelled", "canceled", "withdrawn", "filled"}
)


def is_source_explicitly_closed(source_status: str | None) -> bool:
    if source_status is None:
        return False
    return source_status.strip().lower() in _CLOSED_STATUSES


def is_deadline_expired(deadline: date | None, as_of: date) -> bool:
    if deadline is None:
        return False
    return deadline < as_of


def resolve_lifecycle_status(
    *,
    is_new_opportunity: bool,
    has_material_changes: bool,
    normalized: NormalizedOpportunity,
    as_of: date,
) -> LifecycleStatus:
    if is_source_explicitly_closed(normalized.source_status):
        return LifecycleStatus.CLOSED
    if is_deadline_expired(normalized.deadline, as_of):
        return LifecycleStatus.EXPIRED
    if is_new_opportunity:
        return LifecycleStatus.NEW
    if has_material_changes:
        return LifecycleStatus.UPDATED
    return LifecycleStatus.STILL_OPEN
