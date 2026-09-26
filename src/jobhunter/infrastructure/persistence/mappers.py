"""Explicit mapping between domain objects and persistence rows."""

from __future__ import annotations

from jobhunter.domain import (
    JobSource,
    Opportunity,
    OpportunityChange,
    OpportunityObservation,
    OpportunitySource,
    RawOpportunity,
)
from jobhunter.domain.opportunity_enums import MaterialChangeField
from jobhunter.domain.enums import (
    EligibilityStatus,
    LifecycleStatus,
    OpportunityType,
)
from jobhunter.infrastructure.persistence.models import (
    JobSourceRow,
    OpportunityChangeRow,
    OpportunityObservationRow,
    OpportunityRow,
    OpportunitySourceRow,
    RawOpportunityRow,
)


def job_source_to_row(entity: JobSource) -> JobSourceRow:
    return JobSourceRow(
        id=entity.id,
        name=entity.name,
        organisation=entity.organisation,
        url=entity.url,
        is_active=entity.is_active,
    )


def job_source_to_domain(row: JobSourceRow) -> JobSource:
    return JobSource(
        id=row.id,
        name=row.name,
        organisation=row.organisation,
        url=row.url,
        is_active=row.is_active,
    )


def raw_opportunity_to_row(entity: RawOpportunity) -> RawOpportunityRow:
    return RawOpportunityRow(
        id=entity.id,
        source_id=entity.source_id,
        source_reference=entity.source_reference,
        source_url=entity.source_url,
        retrieved_at=entity.retrieved_at,
        raw_title=entity.raw_title,
        raw_organisation=entity.raw_organisation,
        raw_location=entity.raw_location,
        raw_deadline=entity.raw_deadline,
        raw_description=entity.raw_description,
        extra=dict(entity.extra),
    )


def raw_opportunity_to_domain(row: RawOpportunityRow) -> RawOpportunity:
    return RawOpportunity(
        id=row.id,
        source_id=row.source_id,
        source_reference=row.source_reference,
        source_url=row.source_url,
        retrieved_at=row.retrieved_at,
        raw_title=row.raw_title,
        raw_organisation=row.raw_organisation,
        raw_location=row.raw_location,
        raw_deadline=row.raw_deadline,
        raw_description=row.raw_description,
        extra=dict(row.extra or {}),
    )


def opportunity_to_row(entity: Opportunity) -> OpportunityRow:
    return OpportunityRow(
        id=entity.id,
        title=entity.title,
        organisation=entity.organisation,
        location=entity.location,
        description=entity.description,
        publication_date=entity.publication_date,
        deadline=entity.deadline,
        expected_start_date=entity.expected_start_date,
        opportunity_type=entity.opportunity_type.value,
        lifecycle_status=entity.lifecycle_status.value,
        eligibility_status=entity.eligibility_status.value,
        canonical_identity_key=entity.canonical_identity_key,
        source_status=entity.source_status,
    )


def opportunity_to_domain(row: OpportunityRow) -> Opportunity:
    return Opportunity(
        id=row.id,
        title=row.title,
        organisation=row.organisation,
        location=row.location,
        description=row.description,
        publication_date=row.publication_date,
        deadline=row.deadline,
        expected_start_date=row.expected_start_date,
        opportunity_type=OpportunityType(row.opportunity_type),
        lifecycle_status=LifecycleStatus(row.lifecycle_status),
        eligibility_status=EligibilityStatus(row.eligibility_status),
        canonical_identity_key=row.canonical_identity_key,
        source_status=row.source_status,
    )


def opportunity_source_to_row(entity: OpportunitySource) -> OpportunitySourceRow:
    return OpportunitySourceRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        source_id=entity.source_id,
        source_reference=entity.source_reference,
        source_url=entity.source_url,
        original_url=entity.original_url,
        first_seen_at=entity.first_seen_at,
        last_seen_at=entity.last_seen_at,
    )


def opportunity_source_to_domain(row: OpportunitySourceRow) -> OpportunitySource:
    return OpportunitySource(
        id=row.id,
        opportunity_id=row.opportunity_id,
        source_id=row.source_id,
        source_reference=row.source_reference,
        source_url=row.source_url,
        original_url=row.original_url,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
    )


def opportunity_observation_to_row(
    entity: OpportunityObservation,
) -> OpportunityObservationRow:
    return OpportunityObservationRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        raw_opportunity_id=entity.raw_opportunity_id,
        observed_at=entity.observed_at,
        lifecycle_status=entity.lifecycle_status.value,
    )


def opportunity_observation_to_domain(
    row: OpportunityObservationRow,
) -> OpportunityObservation:
    return OpportunityObservation(
        id=row.id,
        opportunity_id=row.opportunity_id,
        raw_opportunity_id=row.raw_opportunity_id,
        observed_at=row.observed_at,
        lifecycle_status=LifecycleStatus(row.lifecycle_status),
    )


def opportunity_change_to_row(entity: OpportunityChange) -> OpportunityChangeRow:
    return OpportunityChangeRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        observation_id=entity.observation_id,
        field_name=entity.field_name.value,
        previous_value=entity.previous_value,
        new_value=entity.new_value,
        observed_at=entity.observed_at,
    )


def opportunity_change_to_domain(row: OpportunityChangeRow) -> OpportunityChange:
    return OpportunityChange(
        id=row.id,
        opportunity_id=row.opportunity_id,
        observation_id=row.observation_id,
        field_name=MaterialChangeField(row.field_name),
        previous_value=row.previous_value,
        new_value=row.new_value,
        observed_at=row.observed_at,
    )
