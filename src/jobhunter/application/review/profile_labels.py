"""Resolve profile entity IDs to display labels for assessment detail."""

from __future__ import annotations

from sqlalchemy.orm import Session

from jobhunter.infrastructure.persistence.profile_repositories import (
    AssignmentRepository,
    CapabilityRepository,
    CountryExperienceRepository,
    LanguageCapabilityRepository,
    ProfessionalServiceRepository,
    SkillRepository,
)


class ProfileLabelResolver:
    def __init__(self, session: Session) -> None:
        self._services = ProfessionalServiceRepository(session)
        self._assignments = AssignmentRepository(session)
        self._capabilities = CapabilityRepository(session)
        self._skills = SkillRepository(session)
        self._languages = LanguageCapabilityRepository(session)
        self._countries = CountryExperienceRepository(session)
        self._cache: dict[str, str] = {}

    def resolve(self, entity_id: str) -> str:
        if entity_id in self._cache:
            return self._cache[entity_id]
        label = self._lookup(entity_id)
        self._cache[entity_id] = label
        return label

    def _lookup(self, entity_id: str) -> str:
        for repo, attr in (
            (self._services, "name"),
            (self._assignments, "project_name"),
            (self._capabilities, "name"),
            (self._skills, "name"),
            (self._languages, "language_code"),
            (self._countries, "country"),
        ):
            entity = repo.get_by_id(entity_id)
            if entity is not None:
                value = getattr(entity, attr, None)
                if value:
                    return str(value)
        return entity_id

    def build_map_for_result(self, result: dict | None) -> dict[str, str]:
        if not result:
            return {}
        ids: set[str] = set()
        for item in result.get("service_alignments") or []:
            if pid := item.get("professional_service_id"):
                ids.add(str(pid))
        for key in (
            "assignment_evidence",
            "capability_evidence",
            "skill_evidence",
            "language_evidence",
            "country_evidence",
        ):
            for item in result.get(key) or []:
                if eid := item.get("entity_id"):
                    ids.add(str(eid))
        return {entity_id: self.resolve(entity_id) for entity_id in ids}
