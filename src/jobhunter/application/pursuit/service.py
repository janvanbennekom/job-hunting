"""Pursuit/application tracking commands and queries."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.application.pursuit.current_state import current_pursuit_status
from jobhunter.application.pursuit.dtos import (
    ApplicationQueueFilters,
    ApplicationQueueItem,
    PursuitCurrentView,
    PursuitOperationalUpdate,
    PursuitStatusHistoryEntry,
)
from jobhunter.application.pursuit.transitions import validate_pursuit_transition
from jobhunter.application.review.source_links import pick_primary_source_link
from jobhunter.domain.opportunity_pursuit import (
    OpportunityPursuit,
    OpportunityPursuitStatusEvent,
)
from jobhunter.domain.pursuit_enums import (
    TERMINAL_PURSUIT_STATUSES,
    PursuitStatus,
)
from jobhunter.infrastructure.persistence.repositories import (
    JobSourceRepository,
    OpportunityRepository,
    OpportunitySourceRepository,
)
from jobhunter.infrastructure.persistence.pursuit_repositories import (
    OpportunityPursuitRepository,
    OpportunityPursuitStatusEventRepository,
)


class PursuitTrackingService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._opportunities = OpportunityRepository(session)
        self._pursuits = OpportunityPursuitRepository(session)
        self._events = OpportunityPursuitStatusEventRepository(session)

    def start_pursuit(
        self,
        opportunity_id: str,
        *,
        notes: str | None = None,
        operational: PursuitOperationalUpdate | None = None,
        started_at: datetime | None = None,
    ) -> PursuitCurrentView:
        if self._opportunities.get_by_id(opportunity_id) is None:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        if self._pursuits.get_by_opportunity_id(opportunity_id) is not None:
            raise ValueError(
                f"Pursuit tracking already exists for opportunity {opportunity_id}"
            )
        when = started_at or datetime.now(timezone.utc)
        pursuit = OpportunityPursuit(
            opportunity_id=opportunity_id,
            started_at=when,
        )
        if operational:
            self._apply_operational(pursuit, operational, when)
        pursuit = self._pursuits.save(pursuit)
        event = OpportunityPursuitStatusEvent(
            pursuit_id=pursuit.id,
            opportunity_id=opportunity_id,
            recorded_at=when,
            status=PursuitStatus.CONSIDERING,
            notes=notes.strip() if notes and notes.strip() else None,
        )
        self._events.save(event)
        return self.get_current(opportunity_id)

    def record_status_transition(
        self,
        opportunity_id: str,
        new_status: PursuitStatus,
        *,
        notes: str | None = None,
        effective_date: date | None = None,
        recorded_at: datetime | None = None,
    ) -> PursuitCurrentView:
        pursuit = self._require_pursuit(opportunity_id)
        events = self._events.list_for_pursuit(pursuit.id)
        current = current_pursuit_status(events)
        validate_pursuit_transition(current, new_status)
        when = recorded_at or datetime.now(timezone.utc)
        event = OpportunityPursuitStatusEvent(
            pursuit_id=pursuit.id,
            opportunity_id=opportunity_id,
            recorded_at=when,
            status=new_status,
            notes=notes.strip() if notes and notes.strip() else None,
            effective_date=effective_date,
        )
        self._events.save(event)
        return self.get_current(opportunity_id)

    def update_operational(
        self,
        opportunity_id: str,
        update: PursuitOperationalUpdate,
    ) -> PursuitCurrentView:
        pursuit = self._require_pursuit(opportunity_id)
        when = datetime.now(timezone.utc)
        self._apply_operational(pursuit, update, when)
        self._pursuits.save(pursuit)
        return self.get_current(opportunity_id)

    def get_current(self, opportunity_id: str) -> PursuitCurrentView | None:
        pursuit = self._pursuits.get_by_opportunity_id(opportunity_id)
        if pursuit is None:
            return None
        events = self._events.list_for_pursuit(pursuit.id)
        status = current_pursuit_status(events)
        if status is None:
            return None
        history = [
            PursuitStatusHistoryEntry(
                recorded_at=e.recorded_at,
                status=e.status,
                notes=e.notes,
                effective_date=e.effective_date,
            )
            for e in sorted(
                events,
                key=lambda x: (x.recorded_at, x.id),
            )
        ]
        return PursuitCurrentView(
            pursuit_id=pursuit.id,
            opportunity_id=pursuit.opportunity_id,
            started_at=pursuit.started_at,
            current_status=status,
            is_terminal=status in TERMINAL_PURSUIT_STATUSES,
            submission_deadline=pursuit.submission_deadline,
            submission_url=pursuit.submission_url,
            next_action=pursuit.next_action,
            next_action_date=pursuit.next_action_date,
            contact_name=pursuit.contact_name,
            contact_organisation=pursuit.contact_organisation,
            contact_email=pursuit.contact_email,
            reference_identifier=pursuit.reference_identifier,
            history=history,
        )

    def list_status_history(
        self, opportunity_id: str
    ) -> list[PursuitStatusHistoryEntry]:
        view = self.get_current(opportunity_id)
        if view is None:
            return []
        return list(view.history)

    def _require_pursuit(self, opportunity_id: str) -> OpportunityPursuit:
        pursuit = self._pursuits.get_by_opportunity_id(opportunity_id)
        if pursuit is None:
            raise ValueError(
                f"No pursuit tracking for opportunity {opportunity_id}; "
                "start pursuit first."
            )
        return pursuit

    def _apply_operational(
        self,
        pursuit: OpportunityPursuit,
        update: PursuitOperationalUpdate,
        when: datetime,
    ) -> None:
        if update.submission_deadline is not None:
            pursuit.submission_deadline = update.submission_deadline
        if update.submission_url is not None:
            pursuit.submission_url = (
                update.submission_url.strip() if update.submission_url.strip() else None
            )
        if update.next_action is not None:
            pursuit.next_action = (
                update.next_action.strip() if update.next_action.strip() else None
            )
        if update.next_action_date is not None:
            pursuit.next_action_date = update.next_action_date
        if update.contact_name is not None:
            pursuit.contact_name = (
                update.contact_name.strip() if update.contact_name.strip() else None
            )
        if update.contact_organisation is not None:
            pursuit.contact_organisation = (
                update.contact_organisation.strip()
                if update.contact_organisation.strip()
                else None
            )
        if update.contact_email is not None:
            pursuit.contact_email = (
                update.contact_email.strip() if update.contact_email.strip() else None
            )
        if update.reference_identifier is not None:
            pursuit.reference_identifier = (
                update.reference_identifier.strip()
                if update.reference_identifier.strip()
                else None
            )
        pursuit.operational_updated_at = when


class ApplicationQueueQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._pursuits = OpportunityPursuitRepository(session)
        self._events = OpportunityPursuitStatusEventRepository(session)
        self._opportunities = OpportunityRepository(session)
        self._opp_sources = OpportunitySourceRepository(session)
        self._job_sources = JobSourceRepository(session)
        self._tracking = PursuitTrackingService(session)
    def list_queue(
        self, filters: ApplicationQueueFilters | None = None
    ) -> list[ApplicationQueueItem]:
        from jobhunter.application.review.active_strategy import (
            ActiveSearchStrategyResolver,
        )
        from jobhunter.application.review.opportunity_reads import (
            OpportunityPipelineReader,
        )

        resolved = filters or ApplicationQueueFilters()
        today = date.today()
        items: list[ApplicationQueueItem] = []
        ctx = ActiveSearchStrategyResolver(self._session).resolve()
        pipeline_reader = OpportunityPipelineReader(self._session)

        for pursuit in self._pursuits.list_all():
            opp = self._opportunities.get_by_id(pursuit.opportunity_id)
            if opp is None:
                continue
            view = self._tracking.get_current(pursuit.opportunity_id)
            if view is None:
                continue
            if resolved.status is not None and view.current_status != resolved.status:
                continue
            if resolved.active_only and view.is_terminal:
                continue
            if resolved.completed_only and not view.is_terminal:
                continue
            overdue = bool(
                view.next_action_date is not None
                and view.next_action_date < today
                and not view.is_terminal
            )
            if resolved.overdue_next_action and not overdue:
                continue
            approaching = False
            if (
                resolved.upcoming_deadline_days is not None
                and view.submission_deadline is not None
                and not view.is_terminal
            ):
                delta = (view.submission_deadline - today).days
                approaching = 0 <= delta <= resolved.upcoming_deadline_days
                if not approaching:
                    continue

            links = self._opp_sources.list_for_opportunity(opp.id)
            primary = pick_primary_source_link(links, self._job_sources)
            pipeline = pipeline_reader.load(
                opp, ctx.revision_id, allow_fake=False
            )
            band = None
            if pipeline.display_ranking and pipeline.display_ranking.priority_band:
                band = pipeline.display_ranking.priority_band.value

            items.append(
                ApplicationQueueItem(
                    opportunity_id=opp.id,
                    title=opp.title,
                    organisation=opp.organisation,
                    source_name=primary.source_name if primary else None,
                    primary_url=primary.source_url if primary else None,
                    current_status=view.current_status,
                    is_terminal=view.is_terminal,
                    submission_deadline=view.submission_deadline,
                    next_action=view.next_action,
                    next_action_date=view.next_action_date,
                    priority_band=band,
                    next_action_overdue=overdue,
                    deadline_approaching=approaching,
                )
            )

        return sorted(
            items,
            key=lambda i: (
                i.next_action_date or date.max,
                i.submission_deadline or date.max,
                i.title,
            ),
        )
