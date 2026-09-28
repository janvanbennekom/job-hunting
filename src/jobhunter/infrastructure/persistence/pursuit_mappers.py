"""Mappers for opportunity pursuit tracking."""

from __future__ import annotations

from jobhunter.domain.opportunity_pursuit import (
    OpportunityPursuit,
    OpportunityPursuitStatusEvent,
)
from jobhunter.domain.pursuit_enums import PursuitStatus
from jobhunter.infrastructure.persistence.models import (
    OpportunityPursuitRow,
    OpportunityPursuitStatusEventRow,
)


def pursuit_to_row(entity: OpportunityPursuit) -> OpportunityPursuitRow:
    return OpportunityPursuitRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        started_at=entity.started_at,
        submission_deadline=entity.submission_deadline,
        submission_url=entity.submission_url,
        next_action=entity.next_action,
        next_action_date=entity.next_action_date,
        contact_name=entity.contact_name,
        contact_organisation=entity.contact_organisation,
        contact_email=entity.contact_email,
        reference_identifier=entity.reference_identifier,
        operational_updated_at=entity.operational_updated_at,
    )


def pursuit_to_domain(row: OpportunityPursuitRow) -> OpportunityPursuit:
    return OpportunityPursuit(
        id=row.id,
        opportunity_id=row.opportunity_id,
        started_at=row.started_at,
        submission_deadline=row.submission_deadline,
        submission_url=row.submission_url,
        next_action=row.next_action,
        next_action_date=row.next_action_date,
        contact_name=row.contact_name,
        contact_organisation=row.contact_organisation,
        contact_email=row.contact_email,
        reference_identifier=row.reference_identifier,
        operational_updated_at=row.operational_updated_at,
    )


def pursuit_event_to_row(
    entity: OpportunityPursuitStatusEvent,
) -> OpportunityPursuitStatusEventRow:
    return OpportunityPursuitStatusEventRow(
        id=entity.id,
        pursuit_id=entity.pursuit_id,
        opportunity_id=entity.opportunity_id,
        recorded_at=entity.recorded_at,
        status=entity.status.value,
        notes=entity.notes,
        effective_date=entity.effective_date,
    )


def pursuit_event_to_domain(
    row: OpportunityPursuitStatusEventRow,
) -> OpportunityPursuitStatusEvent:
    return OpportunityPursuitStatusEvent(
        id=row.id,
        pursuit_id=row.pursuit_id,
        opportunity_id=row.opportunity_id,
        recorded_at=row.recorded_at,
        status=PursuitStatus(row.status),
        notes=row.notes,
        effective_date=row.effective_date,
    )
