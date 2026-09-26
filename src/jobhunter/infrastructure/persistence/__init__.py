"""PostgreSQL persistence (SQLAlchemy)."""

from jobhunter.infrastructure.persistence.database import (
    create_engine_from_settings,
    create_session_factory,
    session_scope,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    AssignmentCapabilityRepository,
    AssignmentRepository,
    CapabilityRepository,
    CountryExperienceRepository,
    LanguageCapabilityRepository,
    ProfessionalProfileRepository,
    ProfessionalServiceRepository,
    ProfileDocumentRepository,
    SkillRepository,
)
from jobhunter.infrastructure.persistence.repositories import (
    JobSourceRepository,
    OpportunityRepository,
    OpportunitySourceRepository,
    RawOpportunityRepository,
)

__all__ = [
    "AssignmentCapabilityRepository",
    "AssignmentRepository",
    "CapabilityRepository",
    "CountryExperienceRepository",
    "JobSourceRepository",
    "LanguageCapabilityRepository",
    "OpportunityRepository",
    "OpportunitySourceRepository",
    "ProfessionalProfileRepository",
    "ProfessionalServiceRepository",
    "ProfileDocumentRepository",
    "RawOpportunityRepository",
    "SkillRepository",
    "create_engine_from_settings",
    "create_session_factory",
    "session_scope",
]
