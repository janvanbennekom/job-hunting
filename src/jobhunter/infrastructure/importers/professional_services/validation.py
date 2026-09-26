"""Validate professional services seed before apply."""

from __future__ import annotations

from collections import Counter

from jobhunter.infrastructure.importers.professional_services.types import (
    ProfessionalServicesSeed,
)


def validate_seed(seed: ProfessionalServicesSeed) -> list[str]:
    errors: list[str] = []

    if seed.schema_version != 1:
        errors.append(f"Unsupported schema_version {seed.schema_version}")

    if not seed.source_reference:
        errors.append("source_reference is required")

    if not seed.document_title:
        errors.append("source_document.title is required")

    if not seed.profile_display_name:
        errors.append("professional_profile.display_name is required")

    keys = [s.key for s in seed.services]
    for key, count in Counter(keys).items():
        if count > 1:
            errors.append(f"Duplicate service key: {key}")
        if not key:
            errors.append("Service key must be non-empty")

    for service in seed.services:
        if not service.name:
            errors.append(f"Service {service.key!r}: name is required")
        if service.description is not None and not service.description.strip():
            errors.append(f"Service {service.key!r}: description must be non-empty when set")

    if not seed.services:
        errors.append("At least one service definition is required")

    return errors
