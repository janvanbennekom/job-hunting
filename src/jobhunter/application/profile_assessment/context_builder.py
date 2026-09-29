"""Deterministic profile evidence preselection for assessment."""

from __future__ import annotations

import re

from jobhunter.application.profile_assessment.evidence_loader import (
    ProfessionalEvidenceCatalog,
)
from jobhunter.domain.assignment import Assignment
from jobhunter.domain.assignment_capability import AssignmentCapability
from jobhunter.domain.capability import Capability
from jobhunter.domain.country_experience import CountryExperience
from jobhunter.domain.evidence_context_pack import EvidenceContextPack, SelectedEvidenceItem
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.professional_service import ProfessionalService
from jobhunter.domain.skill import Skill

_MAX_ASSIGNMENTS = 5
_MAX_SERVICES = 4
_MAX_CAPABILITIES = 12
_MAX_SKILLS = 15
_MAX_COUNTRY_FALLBACK = 8

_DOMAIN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "land": ("land", "cadastre", "cadastral", "tenure", "registry"),
    "lis": ("lis", "land information", "land administration"),
    "gis": ("gis", "geospatial", "spatial", "mapping"),
    "sdi": ("sdi", "nsdi", "spatial data infrastructure"),
    "integration": ("integration", "interoperability", "middleware"),
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _expand_tokens(base: set[str]) -> set[str]:
    expanded = set(base)
    for token in base:
        for group in _DOMAIN_SYNONYMS.values():
            if token in group:
                expanded.update(group)
    return expanded


def _score_text(opportunity_tokens: set[str], text: str | None) -> int:
    if not text:
        return 0
    doc_tokens = _tokens(text)
    return len(opportunity_tokens & doc_tokens)


def _opportunity_tokens(opportunity: Opportunity) -> set[str]:
    parts = [
        opportunity.title,
        opportunity.description or "",
        opportunity.location or "",
        opportunity.organisation or "",
    ]
    return _expand_tokens(_tokens(" ".join(parts)))


def _select_services(
    services: list[ProfessionalService],
    opportunity_tokens: set[str],
) -> tuple[list[ProfessionalService], list[SelectedEvidenceItem]]:
    active = [s for s in services if s.is_active]
    scored: list[tuple[int, ProfessionalService]] = []
    for svc in active:
        score = _score_text(opportunity_tokens, svc.name)
        score += _score_text(opportunity_tokens, svc.description)
        scored.append((score, svc))
    scored.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    selected = [svc for _, svc in scored[:_MAX_SERVICES]]
    notes = [
        SelectedEvidenceItem(
            entity_type="professional_service",
            entity_id=svc.id,
            selection_reason=f"top service by relevance (score={scored[i][0]})",
        )
        for i, svc in enumerate(selected)
    ]
    return selected, notes


def _select_assignments(
    assignments: list[Assignment],
    opportunity_tokens: set[str],
) -> tuple[list[Assignment], list[SelectedEvidenceItem]]:
    scored: list[tuple[int, Assignment]] = []
    for assignment in assignments:
        text = " ".join(
            filter(
                None,
                [
                    assignment.project_name,
                    assignment.role,
                    assignment.description,
                    assignment.responsibilities,
                    assignment.tools_technologies_text,
                    assignment.country,
                    assignment.donor,
                ],
            )
        )
        score = _score_text(opportunity_tokens, text)
        scored.append((score, assignment))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1].last_active_year or 0,
            item[1].project_name,
        ),
        reverse=True,
    )
    selected = [a for _, a in scored[:_MAX_ASSIGNMENTS]]
    notes = [
        SelectedEvidenceItem(
            entity_type="assignment",
            entity_id=a.id,
            selection_reason=f"top assignment by relevance (score={scored[i][0]})",
        )
        for i, a in enumerate(selected)
    ]
    return selected, notes


def _select_capabilities(
    capabilities: list[Capability],
    assignments: list[Assignment],
    assignment_capabilities: list[AssignmentCapability],
    opportunity_tokens: set[str],
) -> tuple[list[Capability], list[SelectedEvidenceItem]]:
    selected_assignment_ids = {a.id for a in assignments}
    linked_capability_ids = {
        link.capability_id
        for link in assignment_capabilities
        if link.assignment_id in selected_assignment_ids
    }
    scored: list[tuple[int, Capability]] = []
    for capability in capabilities:
        if not capability.is_active:
            continue
        score = _score_text(
            opportunity_tokens,
            f"{capability.name} {capability.code} {capability.description or ''}",
        )
        if capability.id in linked_capability_ids:
            score += 2
        scored.append((score, capability))
    scored.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    selected = [c for _, c in scored[:_MAX_CAPABILITIES]]
    notes = [
        SelectedEvidenceItem(
            entity_type="capability",
            entity_id=c.id,
            selection_reason=f"top capability by relevance (score={scored[i][0]})",
        )
        for i, c in enumerate(selected)
    ]
    return selected, notes


def _select_skills(
    skills: list[Skill],
    opportunity_tokens: set[str],
) -> tuple[list[Skill], list[SelectedEvidenceItem]]:
    scored: list[tuple[int, Skill]] = []
    for skill in skills:
        score = _score_text(opportunity_tokens, skill.name)
        scored.append((score, skill))
    scored.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    selected = [s for _, s in scored[:_MAX_SKILLS]]
    notes = [
        SelectedEvidenceItem(
            entity_type="skill",
            entity_id=s.id,
            selection_reason=f"top skill by relevance (score={scored[i][0]})",
        )
        for i, s in enumerate(selected)
    ]
    return selected, notes


def _select_countries(
    countries: list[CountryExperience],
    opportunity: Opportunity,
    opportunity_tokens: set[str],
) -> tuple[list[CountryExperience], list[SelectedEvidenceItem]]:
    location = (opportunity.location or "").lower()
    matched: list[CountryExperience] = []
    for country in countries:
        name = country.country.lower()
        if name and name in location:
            matched.append(country)

    scored: list[tuple[int, CountryExperience]] = []
    for country in countries:
        if country in matched:
            continue
        score = _score_text(opportunity_tokens, country.country)
        scored.append((score, country))
    scored.sort(key=lambda item: (item[0], item[1].country), reverse=True)

    selected = list(matched)
    for _, country in scored:
        if len(selected) >= _MAX_COUNTRY_FALLBACK:
            break
        if country not in selected:
            selected.append(country)

    notes = [
        SelectedEvidenceItem(
            entity_type="country_experience",
            entity_id=c.id,
            selection_reason=(
                "location match"
                if c.country.lower() in location
                else "relevance fallback"
            ),
        )
        for c in selected
    ]
    return selected, notes


class ProfileEvidenceContextBuilder:
    def build(
        self,
        opportunity: Opportunity,
        catalog: ProfessionalEvidenceCatalog,
        assignment_capabilities: list[AssignmentCapability],
    ) -> EvidenceContextPack:
        opportunity_tokens = _opportunity_tokens(opportunity)
        notes: list[SelectedEvidenceItem] = []

        services, service_notes = _select_services(
            catalog.services, opportunity_tokens
        )
        notes.extend(service_notes)

        assignments, assignment_notes = _select_assignments(
            catalog.assignments, opportunity_tokens
        )
        notes.extend(assignment_notes)

        capabilities, capability_notes = _select_capabilities(
            catalog.capabilities,
            assignments,
            assignment_capabilities,
            opportunity_tokens,
        )
        notes.extend(capability_notes)

        skills, skill_notes = _select_skills(catalog.skills, opportunity_tokens)
        notes.extend(skill_notes)

        countries, country_notes = _select_countries(
            catalog.countries, opportunity, opportunity_tokens
        )
        notes.extend(country_notes)

        for lang in catalog.languages:
            notes.append(
                SelectedEvidenceItem(
                    entity_type="language_capability",
                    entity_id=lang.id,
                    selection_reason="all language capabilities included",
                )
            )

        return EvidenceContextPack(
            positioning_summary=catalog.profile.positioning_summary,
            professional_services=services,
            assignments=assignments,
            capabilities=capabilities,
            skills=skills,
            languages=list(catalog.languages),
            countries=countries,
            selection_notes=notes,
        )
