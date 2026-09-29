"""Reject placeholder or sentinel dates from external APIs."""

from __future__ import annotations

from datetime import date

from jobhunter.domain.serialization import deserialize_optional_date

# Common API sentinels meaning "unknown" or "open-ended".
_PLACEHOLDER_YEARS = frozenset({9999, 10000})


def parse_api_date(raw: str | None) -> date | None:
    """Parse an ISO date string, returning None for missing or placeholder values."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if len(text) >= 10:
        text = text[:10]
    try:
        parsed = deserialize_optional_date(text)
    except ValueError:
        return None
    if parsed.year in _PLACEHOLDER_YEARS:
        return None
    return parsed
