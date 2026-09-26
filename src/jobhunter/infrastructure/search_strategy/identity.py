"""Deterministic identifiers for search strategy seeding."""

from __future__ import annotations

import uuid

from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
    IMPORT_NAMESPACE,
)
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)

DEFAULT_OWNER_KEY = PRIMARY_PROFILE_KEY


def search_strategy_id(owner_key: str = DEFAULT_OWNER_KEY) -> str:
    normalized = owner_key.strip().lower()
    return str(uuid.uuid5(IMPORT_NAMESPACE, f"search-strategy:{normalized}"))


def revision_id_for_content(search_strategy_id: str, content_hash: str) -> str:
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"search-strategy-revision:{search_strategy_id}:{content_hash}",
        )
    )


def theme_id(revision_id: str, theme_key: str) -> str:
    normalized = theme_key.strip().lower()
    return str(
        uuid.uuid5(IMPORT_NAMESPACE, f"search-theme:{revision_id}:{normalized}")
    )


def strategy_criterion_id(revision_id: str, category: str, code: str) -> str:
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"strategy-criterion:{revision_id}:{category}:{code}",
        )
    )


def exclusion_criterion_id(revision_id: str, exclusion_code: str) -> str:
    return str(
        uuid.uuid5(
            IMPORT_NAMESPACE,
            f"exclusion-criterion:{revision_id}:{exclusion_code}",
        )
    )
