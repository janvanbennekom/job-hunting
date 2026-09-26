"""Canonical content hash for strategy revision idempotency (Phase 4A.3)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.domain.strategy_criterion_values import criterion_value_to_mapping


def _canonical_theme(theme) -> dict[str, Any]:
    return {
        "theme_key": theme.theme_key,
        "label": theme.label,
        "strength": theme.strength.value,
        "is_active": theme.is_active,
        "notes": theme.notes,
        "sort_order": theme.sort_order,
    }


def _canonical_criterion(criterion) -> dict[str, Any]:
    return {
        "category": criterion.category.value,
        "code": criterion.code.value,
        "value": criterion_value_to_mapping(criterion.value),
        "strength": (
            criterion.strength.value if criterion.strength is not None else None
        ),
        "is_active": criterion.is_active,
        "notes": criterion.notes,
        "sort_order": criterion.sort_order,
    }


def _canonical_exclusion(exclusion) -> dict[str, Any]:
    return {
        "exclusion_code": exclusion.exclusion_code.value,
        "parameters": exclusion.parameters,
        "is_active": exclusion.is_active,
        "notes": exclusion.notes,
    }


def canonical_content_payload(bundle: RevisionContentBundle) -> dict[str, Any]:
    return {
        "themes": sorted(
            [_canonical_theme(t) for t in bundle.themes],
            key=lambda item: item["theme_key"],
        ),
        "criteria": sorted(
            [_canonical_criterion(c) for c in bundle.criteria],
            key=lambda item: (item["category"], item["code"]),
        ),
        "exclusions": sorted(
            [_canonical_exclusion(e) for e in bundle.exclusions],
            key=lambda item: item["exclusion_code"],
        ),
    }


def compute_revision_content_hash(bundle: RevisionContentBundle) -> str:
    payload = canonical_content_payload(bundle)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
