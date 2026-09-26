"""Deterministic identifiers for country experience evidence."""

from __future__ import annotations

import re
import uuid

from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
    IMPORT_NAMESPACE,
)


def normalize_country_name(country: str) -> str:
    """Normalize country text for stable identity (not display)."""
    collapsed = re.sub(r"\s+", " ", country.strip())
    return collapsed.casefold()


def country_experience_id(source_reference: str, country: str) -> str:
    """Stable id per source document and normalized country name."""
    normalized = normalize_country_name(country)
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"profile-document:{source_reference}:country-experience:{normalized}",
        )
    )
