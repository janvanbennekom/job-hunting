"""Build SET_CRITERION mutations from edited criterion snapshots."""

from __future__ import annotations

import json
from typing import Any


def _normalized(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def build_criterion_mutations(
    originals: list[dict[str, Any]],
    edited: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return SET_CRITERION ops for changed criteria (same order/keys)."""
    mutations: list[dict[str, Any]] = []
    original_by_key = {
        (str(item["category"]), str(item["code"])): item for item in originals
    }
    for item in edited:
        key = (str(item["category"]), str(item["code"]))
        original = original_by_key.get(key)
        if original is None:
            continue
        value_changed = _normalized(original.get("value")) != _normalized(
            item.get("value")
        )
        strength_changed = original.get("strength") != item.get("strength")
        if not value_changed and not strength_changed:
            continue
        mutation: dict[str, Any] = {
            "op": "SET_CRITERION",
            "category": item["category"],
            "code": item["code"],
            "value": item["value"],
        }
        if item.get("strength") is not None:
            mutation["strength"] = item["strength"]
        mutations.append(mutation)
    return mutations
