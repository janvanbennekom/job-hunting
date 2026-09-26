"""Load full professional evidence catalog from persistence."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from jobhunter.domain.assignment import Assignment
from jobhunter.domain.capability import Capability
from jobhunter.domain.country_experience import CountryExperience
from jobhunter.domain.language_capability import LanguageCapability
from jobhunter.domain.professional_profile import ProfessionalProfile
from jobhunter.domain.professional_service import ProfessionalService
from jobhunter.domain.skill import Skill
from jobhunter.infrastructure.importers.professional_services.identity import (
    professional_profile_id,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    AssignmentRepository,
    CapabilityRepository,
    CountryExperienceRepository,
    LanguageCapabilityRepository,
    ProfessionalProfileRepository,
    ProfessionalServiceRepository,
    SkillRepository,
)


@dataclass(frozen=True, slots=True)
class ProfessionalEvidenceCatalog:
    profile: ProfessionalProfile
    services: list[ProfessionalService]
    assignments: list[Assignment]
    capabilities: list[Capability]
    skills: list[Skill]
    languages: list[LanguageCapability]
    countries: list[CountryExperience]


class ProfessionalEvidenceLoader:
    def __init__(self, session: Session) -> None:
        self._profiles = ProfessionalProfileRepository(session)
        self._services = ProfessionalServiceRepository(session)
        self._assignments = AssignmentRepository(session)
        self._capabilities = CapabilityRepository(session)
        self._skills = SkillRepository(session)
        self._languages = LanguageCapabilityRepository(session)
        self._countries = CountryExperienceRepository(session)

    def load_primary(self) -> ProfessionalEvidenceCatalog:
        profile = self._profiles.get_by_id(professional_profile_id())
        if profile is None:
            raise RuntimeError("Primary professional profile is not loaded in the database")

        return ProfessionalEvidenceCatalog(
            profile=profile,
            services=self._services.list_all(),
            assignments=self._assignments.list_all(),
            capabilities=self._capabilities.list_all(),
            skills=self._skills.list_all(),
            languages=self._languages.list_all(),
            countries=self._countries.list_all(),
        )
