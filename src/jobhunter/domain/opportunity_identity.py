"""Deterministic canonical identity for opportunities."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from jobhunter.domain.raw_opportunity import RawOpportunity


def _normalize_reference(value: str) -> str:
    return " ".join(value.strip().lower().split())


def canonicalize_source_url(url: str | None) -> str | None:
    """Normalize a source URL for stable identity comparison."""
    if url is None:
        return None
    trimmed = url.strip()
    if not trimmed:
        return None
    parsed = urlparse(trimmed)
    if not parsed.scheme or not parsed.netloc:
        return trimmed.lower().rstrip("/")
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or ""
    # Ignore query/fragment for MVP stability.
    normalized = urlunparse(
        (parsed.scheme.lower(), netloc, path, "", "", "")
    )
    return normalized


def compute_canonical_identity_key(
    source_id: str, raw: RawOpportunity
) -> str | None:
    """
    Stable identity key for matching repeated observations from the same source.

    Returns None when there is insufficient deterministic evidence (no merge).
    """
    if raw.source_reference and raw.source_reference.strip():
        ref = _normalize_reference(raw.source_reference)
        return f"sr:{source_id}:{ref}"
    url = canonicalize_source_url(raw.source_url)
    if url:
        return f"su:{source_id}:{url}"
    global_ref = raw.extra.get("global_reference")
    if isinstance(global_ref, str) and global_ref.strip():
        return f"gr:{_normalize_reference(global_ref)}"
    return None
