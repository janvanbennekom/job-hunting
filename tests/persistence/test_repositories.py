"""PostgreSQL repository integration tests."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from jobhunter.domain import (
    EligibilityStatus,
    JobSource,
    LifecycleStatus,
    Opportunity,
    OpportunitySource,
    OpportunityType,
    RawOpportunity,
)
from jobhunter.infrastructure.persistence.repositories import (
    JobSourceRepository,
    OpportunityRepository,
    OpportunitySourceRepository,
    RawOpportunityRepository,
)

pytestmark = pytest.mark.integration


def test_job_source_round_trip(db_session: Session) -> None:
    repo = JobSourceRepository(db_session)
    source = JobSource(
        id="test-js-001",
        name="UNOPS",
        organisation="United Nations",
        url="https://example.org/unops",
    )
    repo.save(source)
    loaded = repo.get_by_id("test-js-001")
    assert loaded == source


def test_raw_opportunity_round_trip_and_extra_json(db_session: Session) -> None:
    sources = JobSourceRepository(db_session)
    raw_repo = RawOpportunityRepository(db_session)
    source = sources.save(JobSource(id="test-js-raw", name="FAO"))

    retrieved = datetime(2026, 3, 15, 10, 30, tzinfo=timezone.utc)
    raw = RawOpportunity(
        id="test-raw-001",
        source_id=source.id,
        retrieved_at=retrieved,
        raw_title="GIS Specialist",
        extra={"nested": {"k": 1}, "tags": ["gis", "lis"]},
    )
    raw_repo.save(raw)
    loaded = raw_repo.get_by_id("test-raw-001")
    assert loaded is not None
    assert loaded.extra == {"nested": {"k": 1}, "tags": ["gis", "lis"]}
    assert loaded.retrieved_at == retrieved


def test_opportunity_round_trip_enums_and_dates(db_session: Session) -> None:
    repo = OpportunityRepository(db_session)
    opp = Opportunity(
        id="test-opp-001",
        title="Land administration consultant",
        organisation="IFAD",
        publication_date=date(2026, 1, 5),
        deadline=date(2026, 2, 20),
        expected_start_date=date(2026, 4, 1),
        opportunity_type=OpportunityType.CONSULTANCY,
        lifecycle_status=LifecycleStatus.UPDATED,
        eligibility_status=EligibilityStatus.REVIEW_REQUIRED,
    )
    repo.save(opp)
    loaded = repo.get_by_id("test-opp-001")
    assert loaded == opp


def test_opportunity_source_provenance_and_multi_source(db_session: Session) -> None:
    job_sources = JobSourceRepository(db_session)
    opportunities = OpportunityRepository(db_session)
    links = OpportunitySourceRepository(db_session)

    wb = job_sources.save(JobSource(id="test-js-wb", name="World Bank"))
    unjobs = job_sources.save(JobSource(id="test-js-unjobs", name="UNjobs"))
    opp = opportunities.save(
        Opportunity(id="test-opp-multi", title="Senior GIS Specialist")
    )

    seen = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)
    link_wb = links.save(
        OpportunitySource(
            id="test-link-wb",
            opportunity_id=opp.id,
            source_id=wb.id,
            source_reference="WB-100",
            source_url="https://wb.example/100",
            first_seen_at=seen,
            last_seen_at=seen,
        )
    )
    link_unjobs = links.save(
        OpportunitySource(
            id="test-link-uj",
            opportunity_id=opp.id,
            source_id=unjobs.id,
            source_reference="UJ-200",
            source_url="https://unjobs.example/200",
        )
    )

    assert link_wb.opportunity_id == link_unjobs.opportunity_id
    loaded_links = links.list_for_opportunity(opp.id)
    assert {item.id for item in loaded_links} == {"test-link-wb", "test-link-uj"}


def test_opportunity_source_unique_per_opportunity_and_source(
    db_session: Session,
) -> None:
    job_sources = JobSourceRepository(db_session)
    opportunities = OpportunityRepository(db_session)
    links = OpportunitySourceRepository(db_session)

    source = job_sources.save(JobSource(id="test-js-uniq", name="ADB"))
    opp = opportunities.save(Opportunity(id="test-opp-uniq", title="GIS Advisor"))

    links.save(
        OpportunitySource(
            id="test-link-a",
            opportunity_id=opp.id,
            source_id=source.id,
        )
    )
    db_session.flush()

    duplicate = OpportunitySource(
        id="test-link-b",
        opportunity_id=opp.id,
        source_id=source.id,
    )
    with pytest.raises(IntegrityError):
        links.save(duplicate)
    db_session.rollback()
