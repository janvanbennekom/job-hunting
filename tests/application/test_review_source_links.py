"""Unit tests for primary source link selection."""

from __future__ import annotations

from datetime import datetime, timezone

from jobhunter.application.review.source_links import pick_primary_source_link
from jobhunter.domain.opportunity_source import OpportunitySource


class _FakeSources:
    def get_by_id(self, source_id: str):
        return type("JS", (), {"name": f"Name-{source_id}"})()


def test_primary_link_prefers_original_url() -> None:
    older = OpportunitySource(
        id="1",
        opportunity_id="o1",
        source_id="src-a",
        source_url="https://example.com/list",
        original_url="https://example.com/job/1",
        last_seen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = OpportunitySource(
        id="2",
        opportunity_id="o1",
        source_id="src-b",
        source_url="https://other.com/x",
        original_url=None,
        last_seen_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    primary = pick_primary_source_link([older, newer], _FakeSources())
    assert primary is not None
    assert primary.source_id == "src-b"
    assert primary.external_url == "https://other.com/x"

    primary_old = pick_primary_source_link([older], _FakeSources())
    assert primary_old.external_url == "https://example.com/job/1"
