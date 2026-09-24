"""Tests for domain enumerations."""

from jobhunter.domain.enums import (
    EligibilityStatus,
    LifecycleStatus,
    OpportunityType,
)


def test_opportunity_type_values() -> None:
    assert set(OpportunityType) == {
        OpportunityType.CONSULTANCY,
        OpportunityType.EMPLOYMENT,
        OpportunityType.ROSTER,
        OpportunityType.OTHER,
        OpportunityType.UNKNOWN,
    }
    assert OpportunityType.CONSULTANCY.value == "CONSULTANCY"


def test_lifecycle_status_values() -> None:
    assert set(LifecycleStatus) == {
        LifecycleStatus.NEW,
        LifecycleStatus.UPDATED,
        LifecycleStatus.STILL_OPEN,
        LifecycleStatus.CLOSED,
        LifecycleStatus.EXPIRED,
    }


def test_eligibility_status_values() -> None:
    assert set(EligibilityStatus) == {
        EligibilityStatus.UNKNOWN,
        EligibilityStatus.ELIGIBLE,
        EligibilityStatus.INELIGIBLE,
        EligibilityStatus.REVIEW_REQUIRED,
    }
