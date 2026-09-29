"""Tests for ReliefWeb job mapping."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jobhunter.connectors.reliefweb.identity import RELIEFWEB_JOBS_SOURCE_ID
from jobhunter.connectors.reliefweb.mapper import (
    map_reliefweb_job_to_raw_for_scan,
    reliefweb_job_listing_url,
)
from jobhunter.domain.opportunity_structured_facts import parse_structured_facts_from_extra

FIXTURE = Path("tests/fixtures/reliefweb/jobs_sample.json")


def test_maps_listing_application_and_structured_facts() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    record = payload["data"][0]
    retrieved = datetime(2026, 9, 29, tzinfo=timezone.utc)
    raw = map_reliefweb_job_to_raw_for_scan(
        record,
        source_id=RELIEFWEB_JOBS_SOURCE_ID,
        scan_id="scan-rw",
        retrieved_at=retrieved,
    )
    assert raw.source_reference == "4012345"
    assert raw.source_url == reliefweb_job_listing_url("4012345")
    assert "land information system" in (raw.raw_description or "").lower()
    facts = parse_structured_facts_from_extra(raw.extra)
    assert facts.contract_type_label == "Consultancy"
    assert facts.application_url == "https://employer.example.org/apply/4012345"
    assert facts.sectors == ("Food Security",)
