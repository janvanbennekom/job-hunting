"""Slim, deterministic payloads sent to the assessment model (not full domain graphs)."""

from __future__ import annotations

from typing import Any

from jobhunter.domain.assignment import Assignment
from jobhunter.domain.evidence_context_pack import EvidenceContextPack
from jobhunter.domain.professional_service import ProfessionalService

_ASSIGNMENT_DESCRIPTION_MAX = 700
_ASSIGNMENT_RESPONSIBILITIES_MAX = 700
_SERVICE_DESCRIPTION_MAX = 400


def _truncate_field(text: str | None, limit: int) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 1] + "…"


def assignment_to_model_mapping(assignment: Assignment) -> dict[str, Any]:
    """Conservative per-field caps for verbose assignment evidence."""
    raw = assignment.to_mapping()
    raw["description"] = _truncate_field(
        raw.get("description"), _ASSIGNMENT_DESCRIPTION_MAX
    )
    raw["responsibilities"] = _truncate_field(
        raw.get("responsibilities"), _ASSIGNMENT_RESPONSIBILITIES_MAX
    )
    return raw


def professional_service_to_model_mapping(
    service: ProfessionalService,
) -> dict[str, Any]:
    raw = service.to_mapping()
    raw["description"] = _truncate_field(
        raw.get("description"), _SERVICE_DESCRIPTION_MAX
    )
    return raw


def evidence_pack_to_model_mapping(pack: EvidenceContextPack) -> dict[str, Any]:
    """Evidence for OpenAI only — excludes selection_notes (audit/UI metadata)."""
    return {
        "positioning_summary": pack.positioning_summary,
        "professional_services": [
            professional_service_to_model_mapping(svc)
            for svc in pack.professional_services
        ],
        "assignments": [
            assignment_to_model_mapping(item) for item in pack.assignments
        ],
        "capabilities": [c.to_mapping() for c in pack.capabilities],
        "skills": [s.to_mapping() for s in pack.skills],
        "languages": [lang.to_mapping() for lang in pack.languages],
        "countries": [c.to_mapping() for c in pack.countries],
    }
