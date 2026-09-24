"""Domain identifier helpers."""

from __future__ import annotations

import uuid


def new_domain_id() -> str:
    """Return a new opaque domain identifier (not database-generated)."""
    return str(uuid.uuid4())


def require_non_empty(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must be a non-empty string")
    return stripped
