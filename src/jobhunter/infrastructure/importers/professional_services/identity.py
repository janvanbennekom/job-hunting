"""Deterministic identifiers for Professional Services seed."""

from __future__ import annotations

import uuid

from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
    IMPORT_NAMESPACE,
    profile_document_id,
)

PRIMARY_PROFILE_KEY = "jan-van-bennekom-minnema"


def professional_profile_id() -> str:
    return str(uuid.uuid5(IMPORT_NAMESPACE, f"professional-profile:{PRIMARY_PROFILE_KEY}"))


def professional_service_id(source_reference: str, service_key: str) -> str:
    normalized = service_key.strip().lower()
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"profile-document:{source_reference}:professional-service:{normalized}",
        )
    )


__all__ = [
    "IMPORT_NAMESPACE",
    "PRIMARY_PROFILE_KEY",
    "profile_document_id",
    "professional_profile_id",
    "professional_service_id",
]
