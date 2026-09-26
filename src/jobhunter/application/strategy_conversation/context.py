"""Serialize active strategy for AI interpretation."""

from __future__ import annotations

from typing import Any

from jobhunter.domain.strategy_content_hash import canonical_content_payload
from jobhunter.domain.strategy_criterion_values import criterion_value_to_mapping
from jobhunter.infrastructure.persistence.strategy_repositories import (
    PersistedRevisionSnapshot,
)


def snapshot_to_interpretation_context(
    snapshot: PersistedRevisionSnapshot,
) -> dict[str, Any]:
    from jobhunter.domain.revision_content_bundle import RevisionContentBundle

    content = RevisionContentBundle(
        themes=tuple(snapshot.themes),
        criteria=tuple(snapshot.criteria),
        exclusions=tuple(snapshot.exclusions),
    )
    return {
        "revision_id": snapshot.revision.id,
        "revision_number": snapshot.revision.revision_number,
        "content_hash": snapshot.revision.content_hash,
        "change_summary": snapshot.revision.change_summary,
        "content": canonical_content_payload(content),
        "themes": [
            {
                "theme_key": theme.theme_key,
                "label": theme.label,
                "strength": theme.strength.value,
                "is_active": theme.is_active,
            }
            for theme in snapshot.themes
        ],
        "criteria": [
            {
                "category": criterion.category.value,
                "code": criterion.code.value,
                "value": criterion_value_to_mapping(criterion.value),
                "strength": (
                    criterion.strength.value if criterion.strength else None
                ),
                "is_active": criterion.is_active,
            }
            for criterion in snapshot.criteria
        ],
        "exclusions": [
            {
                "exclusion_code": exclusion.exclusion_code.value,
                "is_active": exclusion.is_active,
            }
            for exclusion in snapshot.exclusions
        ],
    }
