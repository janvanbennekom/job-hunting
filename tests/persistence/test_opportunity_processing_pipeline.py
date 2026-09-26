"""Integration tests for Phase 5 opportunity processing."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.opportunity_processing import OpportunityProcessingService
from jobhunter.domain import (
    JobSource,
    LifecycleStatus,
    MaterialChangeField,
    RawOpportunity,
)
from jobhunter.infrastructure.opportunity_processing import FixtureOpportunityNormalizer
from jobhunter.infrastructure.persistence.models import (
    OpportunityChangeRow,
    OpportunityObservationRow,
    OpportunityRow,
    RawOpportunityRow,
)
from jobhunter.infrastructure.persistence.opportunity_processing_repositories import (
    OpportunityChangeRepository,
    OpportunityObservationRepository,
)
from jobhunter.infrastructure.persistence.repositories import (
    JobSourceRepository,
    OpportunityRepository,
    RawOpportunityRepository,
)

pytestmark = pytest.mark.integration

SOURCE_ID = "phase5-test-source"
REF = "PHASE5-REF-001"


@pytest.fixture
def phase5_source(db_session: Session) -> JobSource:
    repo = JobSourceRepository(db_session)
    existing = repo.get_by_id(SOURCE_ID)
    if existing is not None:
        return existing
    return repo.save(
        JobSource(id=SOURCE_ID, name="Phase 5 Fixture Source")
    )


def _service(db_session: Session) -> OpportunityProcessingService:
    return OpportunityProcessingService(
        db_session, FixtureOpportunityNormalizer()
    )


def _raw(
    raw_id: str,
    *,
    title: str = "Land administration consultant",
    deadline: str = "2026-12-31",
    description: str = "Initial description",
    location: str = "Kenya",
    reference: str = REF,
    retrieved_at: datetime | None = None,
    extra: dict | None = None,
) -> RawOpportunity:
    return RawOpportunity(
        id=raw_id,
        source_id=SOURCE_ID,
        retrieved_at=retrieved_at
        or datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        source_reference=reference,
        raw_title=title,
        raw_location=location,
        raw_deadline=deadline,
        raw_description=description,
        extra=extra or {},
    )


def test_new_opportunity(phase5_source: JobSource, db_session: Session) -> None:
    result = _service(db_session).process(_raw("raw-new-001"))
    assert result.created_opportunity is True
    assert result.opportunity.lifecycle_status is LifecycleStatus.NEW
    assert result.opportunity.canonical_identity_key is not None


def test_repeated_ingestion_same_identity(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    first = service.process(_raw("raw-repeat-001"))
    second = service.process(
        _raw(
            "raw-repeat-002",
            retrieved_at=datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc),
        )
    )
    assert first.opportunity.id == second.opportunity.id
    assert (
        OpportunityRepository(db_session).get_by_id(first.opportunity.id)
        is not None
    )
    observations = OpportunityObservationRepository(db_session).list_for_opportunity(
        first.opportunity.id
    )
    assert len(observations) == 2


def test_duplicate_raw_processing_is_idempotent(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    raw = _raw("raw-dup-process-001")
    first = service.process(raw)
    second = service.process(raw)
    assert first.observation.id == second.observation.id
    assert first.opportunity.id == second.opportunity.id


def test_unchanged_opportunity_still_open(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    service.process(_raw("raw-still-001"))
    result = service.process(
        _raw(
            "raw-still-002",
            retrieved_at=datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc),
        )
    )
    assert result.opportunity.lifecycle_status is LifecycleStatus.STILL_OPEN


def test_changed_deadline_updated_with_change_record(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    opp_id = service.process(_raw("raw-deadline-001")).opportunity.id
    result = service.process(
        _raw(
            "raw-deadline-002",
            deadline="2027-01-15",
            retrieved_at=datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc),
        )
    )
    assert result.opportunity.lifecycle_status is LifecycleStatus.UPDATED
    fields = {c.field_name for c in result.changes}
    assert MaterialChangeField.DEADLINE in fields
    all_changes = OpportunityChangeRepository(db_session).list_for_opportunity(
        opp_id
    )
    assert any(c.field_name is MaterialChangeField.DEADLINE for c in all_changes)


def test_changed_description(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    service.process(_raw("raw-desc-001"))
    result = service.process(
        _raw(
            "raw-desc-002",
            description="Revised terms of reference text",
            retrieved_at=datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc),
        )
    )
    assert result.opportunity.lifecycle_status is LifecycleStatus.UPDATED
    assert MaterialChangeField.DESCRIPTION in {c.field_name for c in result.changes}


def test_changed_title_and_location(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    service.process(_raw("raw-loc-001"))
    result = service.process(
        _raw(
            "raw-loc-002",
            title="Senior land administration consultant",
            location="Uganda",
            retrieved_at=datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc),
        )
    )
    fields = {c.field_name for c in result.changes}
    assert MaterialChangeField.TITLE in fields
    assert MaterialChangeField.LOCATION in fields


def test_deadline_passes_expired(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    service.process(_raw("raw-exp-001", deadline="2026-12-31"))
    result = service.process(
        _raw(
            "raw-exp-002",
            deadline="2026-01-01",
            retrieved_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        ),
        as_of=date(2026, 6, 15),
    )
    assert result.opportunity.lifecycle_status is LifecycleStatus.EXPIRED


def test_explicit_source_closure(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    service.process(_raw("raw-close-001"))
    result = service.process(
        _raw(
            "raw-close-002",
            extra={"source_status": "closed"},
            retrieved_at=datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc),
        )
    )
    assert result.opportunity.lifecycle_status is LifecycleStatus.CLOSED


def test_raw_and_observation_provenance_retained(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    service.process(_raw("raw-prov-001"))
    service.process(
        _raw(
            "raw-prov-002",
            retrieved_at=datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc),
        )
    )
    raw_count = db_session.scalar(
        select(func.count()).select_from(RawOpportunityRow).where(
            RawOpportunityRow.source_id == SOURCE_ID,
            RawOpportunityRow.source_reference == REF,
        )
    )
    assert raw_count == 2


def test_observation_linked_to_opportunity(
    phase5_source: JobSource, db_session: Session
) -> None:
    result = _service(db_session).process(_raw("raw-link-001"))
    row = db_session.get(OpportunityObservationRow, result.observation.id)
    assert row is not None
    assert row.opportunity_id == result.opportunity.id
    assert row.raw_opportunity_id == "raw-link-001"


def test_no_duplicate_canonical_opportunities(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    for index in range(3):
        service.process(
            _raw(
                f"raw-canonical-{index}",
                retrieved_at=datetime(2026, 6, 9, index, 0, tzinfo=timezone.utc),
            )
        )
    identity_key = service.process(
        _raw(
            "raw-canonical-check",
            retrieved_at=datetime(2026, 6, 9, 9, 0, tzinfo=timezone.utc),
        )
    ).opportunity.canonical_identity_key
    count = db_session.scalar(
        select(func.count())
        .select_from(OpportunityRow)
        .where(OpportunityRow.canonical_identity_key == identity_key)
    )
    assert count == 1


def test_insufficient_identity_does_not_merge(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    base = datetime(2026, 6, 11, tzinfo=timezone.utc)
    first = service.process(
        RawOpportunity(
            id="raw-no-id-001",
            source_id=SOURCE_ID,
            retrieved_at=base,
            raw_title="First untracked",
        )
    )
    second = service.process(
        RawOpportunity(
            id="raw-no-id-002",
            source_id=SOURCE_ID,
            retrieved_at=base,
            raw_title="Second untracked",
        )
    )
    assert first.opportunity.id != second.opportunity.id


def test_historical_observations_and_changes_remain(
    phase5_source: JobSource, db_session: Session
) -> None:
    service = _service(db_session)
    opp_id = service.process(_raw("raw-hist-001")).opportunity.id
    service.process(
        _raw(
            "raw-hist-002",
            description="Changed once",
            retrieved_at=datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc),
        )
    )
    observations = OpportunityObservationRepository(db_session).list_for_opportunity(
        opp_id
    )
    changes = OpportunityChangeRepository(db_session).list_for_opportunity(opp_id)
    assert len(observations) >= 2
    assert len(changes) >= 1
