"""Core domain models and rules (technology-independent)."""

from jobhunter.domain.assignment import Assignment
from jobhunter.domain.assignment_capability import AssignmentCapability
from jobhunter.domain.capability import Capability
from jobhunter.domain.country_experience import CountryExperience
from jobhunter.domain.enums import (
    EligibilityStatus,
    LifecycleStatus,
    OpportunityType,
)
from jobhunter.domain.identifiers import new_domain_id
from jobhunter.domain.job_source import JobSource
from jobhunter.domain.language_capability import LanguageCapability
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_change import OpportunityChange
from jobhunter.domain.opportunity_enums import MaterialChangeField
from jobhunter.domain.opportunity_observation import OpportunityObservation
from jobhunter.domain.opportunity_source import OpportunitySource
from jobhunter.domain.profile_document import ProfileDocument
from jobhunter.domain.profile_enums import CapabilityCategory, ProfileDocumentType
from jobhunter.domain.professional_profile import ProfessionalProfile
from jobhunter.domain.professional_service import ProfessionalService
from jobhunter.domain.exclusion_criterion import ExclusionCriterion
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.search_strategy import SearchStrategy
from jobhunter.domain.search_strategy_revision import SearchStrategyRevision
from jobhunter.domain.search_theme import SearchTheme
from jobhunter.domain.source_scan import SourceScan
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.domain.skill import Skill
from jobhunter.domain.strategy_criterion import StrategyCriterion
from jobhunter.domain.strategy_enums import (
    ExclusionCode,
    PreferenceStrength,
    RevisionChangeSource,
    RevisionStatus,
    StrategyCriterionCategory,
    StrategyParameterCode,
)

__all__ = [
    "Assignment",
    "AssignmentCapability",
    "Capability",
    "CapabilityCategory",
    "CountryExperience",
    "EligibilityStatus",
    "ExclusionCode",
    "ExclusionCriterion",
    "JobSource",
    "LanguageCapability",
    "LifecycleStatus",
    "MaterialChangeField",
    "NormalizedOpportunity",
    "Opportunity",
    "OpportunityChange",
    "OpportunityObservation",
    "OpportunitySource",
    "OpportunityType",
    "PreferenceStrength",
    "ProfessionalProfile",
    "ProfessionalService",
    "ProfileDocument",
    "ProfileDocumentType",
    "RawOpportunity",
    "RevisionChangeSource",
    "RevisionStatus",
    "SearchStrategy",
    "SearchStrategyRevision",
    "SearchTheme",
    "SourceScan",
    "SourceScanStatus",
    "Skill",
    "StrategyCriterion",
    "StrategyCriterionCategory",
    "StrategyParameterCode",
    "new_domain_id",
]
