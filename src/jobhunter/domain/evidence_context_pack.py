"""Deterministic evidence selection for AI assessment context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.assignment import Assignment
from jobhunter.domain.capability import Capability
from jobhunter.domain.country_experience import CountryExperience
from jobhunter.domain.language_capability import LanguageCapability
from jobhunter.domain.professional_service import ProfessionalService
from jobhunter.domain.skill import Skill


@dataclass(slots=True)
class SelectedEvidenceItem:
    entity_type: str
    entity_id: str
    selection_reason: str


@dataclass(slots=True)
class EvidenceContextPack:
    """Subset of professional evidence supplied to the assessment model."""

    positioning_summary: str | None
    professional_services: list[ProfessionalService]
    assignments: list[Assignment]
    capabilities: list[Capability]
    skills: list[Skill]
    languages: list[LanguageCapability]
    countries: list[CountryExperience]
    selection_notes: list[SelectedEvidenceItem] = field(default_factory=list)

    def allowed_profile_ids(self) -> set[str]:
        ids: set[str] = set()
        for svc in self.professional_services:
            ids.add(svc.id)
        for item in self.assignments:
            ids.add(item.id)
        for item in self.capabilities:
            ids.add(item.id)
        for item in self.skills:
            ids.add(item.id)
        for item in self.languages:
            ids.add(item.id)
        for item in self.countries:
            ids.add(item.id)
        return ids

    def to_mapping(self) -> dict[str, Any]:
        return {
            "positioning_summary": self.positioning_summary,
            "professional_services": [
                svc.to_mapping() for svc in self.professional_services
            ],
            "assignments": [a.to_mapping() for a in self.assignments],
            "capabilities": [c.to_mapping() for c in self.capabilities],
            "skills": [s.to_mapping() for s in self.skills],
            "languages": [lang.to_mapping() for lang in self.languages],
            "countries": [c.to_mapping() for c in self.countries],
            "selection_notes": [
                {
                    "entity_type": n.entity_type,
                    "entity_id": n.entity_id,
                    "selection_reason": n.selection_reason,
                }
                for n in self.selection_notes
            ],
        }
