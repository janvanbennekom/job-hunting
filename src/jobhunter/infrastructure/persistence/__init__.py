"""PostgreSQL persistence (SQLAlchemy)."""

from jobhunter.infrastructure.persistence.database import (
    create_engine_from_settings,
    create_session_factory,
    session_scope,
)
from jobhunter.infrastructure.persistence.repositories import (
    JobSourceRepository,
    OpportunityRepository,
    OpportunitySourceRepository,
    RawOpportunityRepository,
)

__all__ = [
    "JobSourceRepository",
    "OpportunityRepository",
    "OpportunitySourceRepository",
    "RawOpportunityRepository",
    "create_engine_from_settings",
    "create_session_factory",
    "session_scope",
]
