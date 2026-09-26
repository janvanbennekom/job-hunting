"""Core domain models and rules (technology-independent)."""

from jobhunter.domain.assignment import Assignment
from jobhunter.domain.assignment_capability import AssignmentCapability
from jobhunter.domain.capability import Capability
from jobhunter.domain.enums import (
    EligibilityStatus,
    LifecycleStatus,
    OpportunityType,
)
from jobhunter.domain.identifiers import new_domain_id
from jobhunter.domain.job_source import JobSource
from jobhunter.domain.language_capability import LanguageCapability
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_source import OpportunitySource
from jobhunter.domain.profile_document import ProfileDocument
from jobhunter.domain.profile_enums import CapabilityCategory, ProfileDocumentType
from jobhunter.domain.professional_profile import ProfessionalProfile
from jobhunter.domain.professional_service import ProfessionalService
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.skill import Skill

__all__ = [
    "Assignment",
    "AssignmentCapability",
    "Capability",
    "CapabilityCategory",
    "EligibilityStatus",
    "JobSource",
    "LanguageCapability",
    "LifecycleStatus",
    "Opportunity",
    "OpportunitySource",
    "OpportunityType",
    "ProfessionalProfile",
    "ProfessionalService",
    "ProfileDocument",
    "ProfileDocumentType",
    "RawOpportunity",
    "Skill",
    "new_domain_id",
]
