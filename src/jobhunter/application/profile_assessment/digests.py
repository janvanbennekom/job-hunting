"""Canonical digests for assessment idempotency."""

from __future__ import annotations

import hashlib
import json
from datetime import date

from jobhunter.domain.assessment_enums import PROFILE_ASSESSMENT_SCHEMA_VERSION
from jobhunter.domain.assignment import Assignment
from jobhunter.domain.capability import Capability
from jobhunter.domain.country_experience import CountryExperience
from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.language_capability import LanguageCapability
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_structured_facts import OpportunityStructuredFacts
from jobhunter.domain.professional_profile import ProfessionalProfile
from jobhunter.domain.professional_service import ProfessionalService
from jobhunter.domain.skill import Skill


def _sha256_hex(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _date_iso(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def compute_opportunity_content_digest(
    opportunity: Opportunity,
    structured_facts: OpportunityStructuredFacts | None = None,
) -> str:
    payload = {
        "title": opportunity.title,
        "organisation": opportunity.organisation,
        "location": opportunity.location,
        "description": opportunity.description,
        "opportunity_type": opportunity.opportunity_type.value,
        "source_status": opportunity.source_status,
        "deadline": _date_iso(opportunity.deadline),
        "publication_date": _date_iso(opportunity.publication_date),
        "expected_start_date": _date_iso(opportunity.expected_start_date),
    }
    if structured_facts is not None and not structured_facts.is_empty():
        payload["structured_facts"] = structured_facts.to_digest_mapping()
    return _sha256_hex(payload)


def compute_profile_evidence_digest(
    profile: ProfessionalProfile,
    services: list[ProfessionalService],
    assignments: list[Assignment],
    capabilities: list[Capability],
    skills: list[Skill],
    languages: list[LanguageCapability],
    countries: list[CountryExperience],
) -> str:
    payload = {
        "profile_id": profile.id,
        "positioning_summary": profile.positioning_summary,
        "services": sorted(s.id for s in services),
        "assignments": sorted(a.id for a in assignments),
        "capabilities": sorted(c.id for c in capabilities),
        "skills": sorted(s.id for s in skills),
        "languages": sorted(lang.id for lang in languages),
        "countries": sorted(c.id for c in countries),
    }
    return _sha256_hex(payload)


def compute_input_digest(
    *,
    opportunity_content_digest: str,
    profile_evidence_digest: str,
    search_strategy_revision_id: str,
    prompt_schema_version: str,
    model_provider: str,
    model_name: str,
) -> str:
    payload = {
        "opportunity_content_digest": opportunity_content_digest,
        "profile_evidence_digest": profile_evidence_digest,
        "search_strategy_revision_id": search_strategy_revision_id,
        "prompt_schema_version": prompt_schema_version,
        "model_provider": model_provider,
        "model_name": model_name,
    }
    return _sha256_hex(payload)


def default_prompt_schema_version() -> str:
    return PROFILE_ASSESSMENT_SCHEMA_VERSION
