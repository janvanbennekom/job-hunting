"""Core domain models and rules (technology-independent)."""

from jobhunter.domain.enums import (
    EligibilityStatus,
    LifecycleStatus,
    OpportunityType,
)
from jobhunter.domain.identifiers import new_domain_id
from jobhunter.domain.job_source import JobSource
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_source import OpportunitySource
from jobhunter.domain.raw_opportunity import RawOpportunity

__all__ = [
    "EligibilityStatus",
    "JobSource",
    "LifecycleStatus",
    "Opportunity",
    "OpportunitySource",
    "OpportunityType",
    "RawOpportunity",
    "new_domain_id",
]
