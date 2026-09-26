"""Deterministic identifiers for CV profile seed."""

from __future__ import annotations

import uuid

from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
    IMPORT_NAMESPACE,
    profile_document_id,
)
from jobhunter.infrastructure.importers.professional_services.identity import (
    professional_profile_id,
)

__all__ = [
    "profile_document_id",
    "professional_profile_id",
    "skill_id",
    "language_capability_id",
]


def skill_id(source_reference: str, skill_key: str) -> str:
    normalized = skill_key.strip().lower()
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"profile-document:{source_reference}:skill:{normalized}",
        )
    )


def language_capability_id(source_reference: str, language_key: str) -> str:
    normalized = language_key.strip().lower()
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"profile-document:{source_reference}:language:{normalized}",
        )
    )
