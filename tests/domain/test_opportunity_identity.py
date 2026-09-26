"""Tests for deterministic opportunity identity."""

from __future__ import annotations

from datetime import datetime, timezone

from jobhunter.domain.opportunity_identity import (
    canonicalize_source_url,
    compute_canonical_identity_key,
)
from jobhunter.domain.raw_opportunity import RawOpportunity


def test_identity_from_source_reference_is_stable() -> None:
    raw = RawOpportunity(
        source_id="src-1",
        retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_reference="REF-100",
    )
    first = compute_canonical_identity_key("src-1", raw)
    raw2 = RawOpportunity(
        source_id="src-1",
        retrieved_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        source_reference="ref-100",
    )
    second = compute_canonical_identity_key("src-1", raw2)
    assert first == second


def test_identity_from_canonical_url() -> None:
    raw = RawOpportunity(
        source_id="src-1",
        retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_url="https://Example.org/jobs/42/",
    )
    key = compute_canonical_identity_key("src-1", raw)
    assert key is not None
    assert "example.org/jobs/42" in key


def test_insufficient_identity_returns_none() -> None:
    raw = RawOpportunity(
        source_id="src-1",
        retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        raw_title="Untracked",
    )
    assert compute_canonical_identity_key("src-1", raw) is None


def test_canonicalize_url_strips_trailing_slash() -> None:
    assert canonicalize_source_url("https://a.test/x/") == canonicalize_source_url(
        "https://a.test/x"
    )
