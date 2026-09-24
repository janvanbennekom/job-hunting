"""Tests for OpportunitySource and multi-source association."""

from datetime import datetime, timezone

import pytest

from jobhunter.domain import (
    JobSource,
    Opportunity,
    OpportunitySource,
)


def test_opportunity_source_valid_construction() -> None:
    seen = datetime(2026, 3, 1, tzinfo=timezone.utc)
    link = OpportunitySource(
        opportunity_id="opp-1",
        source_id="src-1",
        source_reference="REF-99",
        source_url="https://portal.example/ref-99",
        original_url="https://client.example/tor/ref-99",
        first_seen_at=seen,
        last_seen_at=seen,
    )
    assert link.source_reference == "REF-99"


def test_opportunity_source_requires_timezone_aware_timestamps() -> None:
    naive = datetime(2026, 3, 1, 12, 0)
    with pytest.raises(ValueError, match="first_seen_at"):
        OpportunitySource(
            opportunity_id="o1",
            source_id="s1",
            first_seen_at=naive,
        )


def test_one_opportunity_multiple_sources_without_duplicating_opportunity() -> None:
    opportunity = Opportunity(id="shared-opp", title="Senior GIS Specialist")
    bank = JobSource(id="wb", name="World Bank")
    aggregator = JobSource(id="unjobs", name="UNjobs")

    link_bank = OpportunitySource(
        opportunity_id=opportunity.id,
        source_id=bank.id,
        source_reference="WB-555",
        source_url="https://wb.example/555",
    )
    link_aggregator = OpportunitySource(
        opportunity_id=opportunity.id,
        source_id=aggregator.id,
        source_reference="UJ-999",
        source_url="https://unjobs.example/999",
    )

    assert link_bank.opportunity_id == link_aggregator.opportunity_id
    assert link_bank.source_id != link_aggregator.source_id
    assert link_bank.opportunity_id == opportunity.id


def test_opportunity_source_mapping_roundtrip() -> None:
    seen = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)
    link = OpportunitySource(
        id="link-1",
        opportunity_id="opp-1",
        source_id="src-1",
        first_seen_at=seen,
    )
    restored = OpportunitySource.from_mapping(link.to_mapping())
    assert restored == link
