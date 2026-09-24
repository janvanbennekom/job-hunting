"""Tests for Opportunity."""

from datetime import date

import pytest

from jobhunter.domain import (
    EligibilityStatus,
    LifecycleStatus,
    Opportunity,
    OpportunityType,
)


def test_opportunity_valid_construction_and_defaults() -> None:
    opp = Opportunity(title="LIS Implementation Specialist")
    assert opp.lifecycle_status is LifecycleStatus.NEW
    assert opp.eligibility_status is EligibilityStatus.UNKNOWN
    assert opp.opportunity_type is OpportunityType.UNKNOWN
    assert opp.id


def test_opportunity_with_normalized_fields() -> None:
    opp = Opportunity(
        id="opp-1",
        title="GIS Consultant",
        organisation="IFAD",
        location="Rome, Italy",
        description="Implementation support",
        publication_date=date(2026, 1, 10),
        deadline=date(2026, 2, 28),
        expected_start_date=date(2026, 4, 1),
        opportunity_type=OpportunityType.CONSULTANCY,
        lifecycle_status=LifecycleStatus.STILL_OPEN,
        eligibility_status=EligibilityStatus.REVIEW_REQUIRED,
    )
    assert opp.deadline == date(2026, 2, 28)
    assert opp.opportunity_type is OpportunityType.CONSULTANCY


def test_opportunity_rejects_empty_title() -> None:
    with pytest.raises(ValueError, match="title"):
        Opportunity(title="  ")


def test_opportunity_has_no_intrinsic_source_url_field() -> None:
    assert "source_url" not in Opportunity.__dataclass_fields__


def test_opportunity_mapping_roundtrip() -> None:
    opp = Opportunity(
        id="opp-2",
        title="Land administration advisor",
        opportunity_type=OpportunityType.CONSULTANCY,
        lifecycle_status=LifecycleStatus.UPDATED,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        deadline=date(2026, 5, 1),
    )
    restored = Opportunity.from_mapping(opp.to_mapping())
    assert restored == opp
