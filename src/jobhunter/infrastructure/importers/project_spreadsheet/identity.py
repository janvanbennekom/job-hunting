"""Deterministic domain identifiers for spreadsheet import."""

from __future__ import annotations

import uuid

# Fixed namespace for reproducible import IDs across runs.
IMPORT_NAMESPACE = uuid.UUID("8f3e2b1a-9c4d-5e6f-a7b8-c1d2e3f4a5b6")


def profile_document_id(source_reference: str) -> str:
    return str(uuid.uuid5(IMPORT_NAMESPACE, f"profile-document:{source_reference}"))


def capability_id(code: str) -> str:
    return str(uuid.uuid5(IMPORT_NAMESPACE, f"capability:{code.strip().lower()}"))


def assignment_id(source_reference: str, sequence: int) -> str:
    """Stable per source document and Project.sequence (layout-independent)."""
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"profile-document:{source_reference}:assignment:{sequence}",
        )
    )


def assignment_capability_id(assignment_id_value: str, capability_id_value: str) -> str:
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"assignment-capability:{assignment_id_value}:{capability_id_value}",
        )
    )
