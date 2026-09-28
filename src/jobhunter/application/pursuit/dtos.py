"""DTOs for pursuit/application tracking UI and queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from jobhunter.domain.pursuit_enums import PursuitStatus


@dataclass(slots=True)
class PursuitOperationalUpdate:
    submission_deadline: date | None = None
    submission_url: str | None = None
    next_action: str | None = None
    next_action_date: date | None = None
    contact_name: str | None = None
    contact_organisation: str | None = None
    contact_email: str | None = None
    reference_identifier: str | None = None


@dataclass(slots=True)
class PursuitStatusHistoryEntry:
    recorded_at: datetime
    status: PursuitStatus
    notes: str | None
    effective_date: date | None


@dataclass(slots=True)
class PursuitCurrentView:
    pursuit_id: str
    opportunity_id: str
    started_at: datetime
    current_status: PursuitStatus
    is_terminal: bool
    submission_deadline: date | None
    submission_url: str | None
    next_action: str | None
    next_action_date: date | None
    contact_name: str | None
    contact_organisation: str | None
    contact_email: str | None
    reference_identifier: str | None
    history: list[PursuitStatusHistoryEntry] = field(default_factory=list)


@dataclass(slots=True)
class ApplicationQueueFilters:
    active_only: bool = True
    completed_only: bool = False
    status: PursuitStatus | None = None
    overdue_next_action: bool = False
    upcoming_deadline_days: int | None = None


@dataclass(slots=True)
class ApplicationQueueItem:
    opportunity_id: str
    title: str
    organisation: str | None
    source_name: str | None
    primary_url: str | None
    current_status: PursuitStatus
    is_terminal: bool
    submission_deadline: date | None
    next_action: str | None
    next_action_date: date | None
    priority_band: str | None
    next_action_overdue: bool
    deadline_approaching: bool
