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
from jobhunter.infrastructure.persistence.strategy_repositories import (
    ExclusionCriterionRepository,
    PersistedRevisionSnapshot,
    SearchStrategyRepository,
    SearchStrategyRevisionRepository,
    SearchThemeRepository,
    StrategyCriterionRepository,
    StrategyRevisionSnapshotRepository,
)

__all__ = [
    "AssignmentCapabilityRepository",
    "AssignmentRepository",
    "CapabilityRepository",
    "CountryExperienceRepository",
    "ExclusionCriterionRepository",
    "JobSourceRepository",
    "LanguageCapabilityRepository",
    "OpportunityRepository",
    "OpportunitySourceRepository",
    "ProfessionalProfileRepository",
    "ProfessionalServiceRepository",
    "PersistedRevisionSnapshot",
    "ProfileDocumentRepository",
    "RawOpportunityRepository",
    "SearchStrategyRepository",
    "SearchStrategyRevisionRepository",
    "SearchThemeRepository",
    "SkillRepository",
    "StrategyCriterionRepository",
    "StrategyRevisionSnapshotRepository",
    "create_engine_from_settings",
    "create_session_factory",
    "session_scope",
]
