"""Tests for DevelopmentAid -> RawOpportunity mapping."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_SOURCE_ID
from jobhunter.connectors.developmentaid.mapper import (
    map_developmentaid_job_to_raw_for_scan,
)
from jobhunter.connectors.developmentaid.normalizer import (
    DevelopmentAidOpportunityNormalizer,
)
from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.opportunity_structured_facts import parse_structured_facts_from_extra

FIXTURE_DIR = Path("tests/fixtures/developmentaid")


def test_maps_stable_source_reference_and_url() -> None:
    items = json.loads((FIXTURE_DIR / "job_search_sample.json").read_text())[
        "items"
    ]
    detail = json.loads((FIXTURE_DIR / "job_detail_900001.json").read_text())
    retrieved = datetime(2026, 9, 27, tzinfo=timezone.utc)
    raw = map_developmentaid_job_to_raw_for_scan(
        items[0],
        source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
        scan_id="scan-da",
        retrieved_at=retrieved,
        detail=detail,
    )
    assert raw.source_reference == "900001"
    assert "/jobs/view/900001/" in raw.source_url
    assert "land information system" in (raw.raw_description or "").lower()
    assert raw.extra["source_listing_id"] == "900001"
    facts = parse_structured_facts_from_extra(raw.extra)
    assert facts.sectors == ("Land Administration",)
    assert facts.languages == ("English",)
    assert facts.minimum_experience_years == 8
    assert facts.organisation_type == "Consulting firm"
    assert "Contract" in (facts.contract_type_label or "")
    assert facts.application_url == "https://employer.example.org/apply/senior-gis"
    assert facts.content_last_updated is not None


def test_normalizer_maps_publication_and_consultancy_type() -> None:
    items = json.loads((FIXTURE_DIR / "job_search_sample.json").read_text())[
        "items"
    ]
    detail = json.loads((FIXTURE_DIR / "job_detail_900001.json").read_text())
    raw = map_developmentaid_job_to_raw_for_scan(
        items[0],
        source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
        scan_id="scan-da",
        retrieved_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
        detail=detail,
    )
    normalized = DevelopmentAidOpportunityNormalizer().normalize(raw)
    assert normalized.publication_date is not None
    assert normalized.opportunity_type is OpportunityType.CONSULTANCY
    assert normalized.location == "Kenya"


def test_sentinel_expected_start_not_persisted() -> None:
    items = json.loads((FIXTURE_DIR / "job_search_sample.json").read_text())[
        "items"
    ]
    detail = json.loads((FIXTURE_DIR / "job_detail_900001.json").read_text())
    detail["expectedStartingDate"] = "9999-12-28"
    raw = map_developmentaid_job_to_raw_for_scan(
        items[0],
        source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
        scan_id="scan-da",
        retrieved_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
        detail=detail,
    )
    normalized = DevelopmentAidOpportunityNormalizer().normalize(raw)
    assert normalized.expected_start_date is None


def test_missing_title_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="title"):
        map_developmentaid_job_to_raw_for_scan(
            {"id": 1},
            source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
            scan_id="x",
            retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
