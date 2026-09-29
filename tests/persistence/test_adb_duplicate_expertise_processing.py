"""ADB rows sharing a notice id must merge before processing (no raw-id collision)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.adb_scan import AdbScanService
from jobhunter.application.opportunity_processing import OpportunityProcessingService
from jobhunter.connectors.adb.connector import AdbCsrnConnector, AdbCsrnScanResult
from jobhunter.connectors.adb.identity import ADB_CSRN_SOURCE_ID
from jobhunter.connectors.adb.mapper import map_adb_notice_to_raw_for_scan
from jobhunter.connectors.adb.normalizer import AdbCsrnOpportunityNormalizer
from jobhunter.application.profile_assessment.digests import (
    compute_opportunity_content_digest,
)
from jobhunter.application.profile_assessment.opportunity_prompt import (
    build_opportunity_prompt_text,
)
from jobhunter.application.opportunity_processing.structured_facts_loader import (
    OpportunityStructuredFactsLoader,
)
from jobhunter.domain.assessment_enums import OpportunityEvidenceField
from jobhunter.infrastructure.persistence.opportunity_processing_repositories import (
    OpportunityObservationRepository,
)
from jobhunter.infrastructure.persistence.repositories import (
    OpportunityRepository,
    RawOpportunityRepository,
)

pytestmark = pytest.mark.integration


def _three_expertise_rows(notice: str = "E-990001-001") -> list[dict]:
    base_title = f"LOAN-6070 CAM: Package ({notice})"
    return [
        {
            "notice_id": notice,
            "title": base_title,
            "expertise": "Land Administration Specialist",
            "consultant_type": "Firm",
            "published": "24-Sep-2026",
            "deadline": "04-Nov-2026 11:59 PM",
            "duration_months": "36",
            "project_number": "59508-001",
            "row_index": 0,
            "listing_url": f"https://example.test/list#notice={notice}",
        },
        {
            "notice_id": notice,
            "title": base_title,
            "expertise": "GIS Specialist",
            "consultant_type": "Firm",
            "published": "24-Sep-2026",
            "deadline": "04-Nov-2026 11:59 PM",
            "duration_months": "36",
            "project_number": "59508-001",
            "row_index": 1,
            "listing_url": f"https://example.test/list#notice={notice}",
        },
        {
            "notice_id": notice,
            "title": base_title,
            "expertise": "Survey Specialist",
            "consultant_type": "Firm",
            "published": "24-Sep-2026",
            "deadline": "04-Nov-2026 11:59 PM",
            "duration_months": "36",
            "project_number": "59508-001",
            "row_index": 2,
            "listing_url": f"https://example.test/list#notice={notice}",
        },
    ]


class _DuplicateRowConnector:
    def fetch_notices(self, *, keyword=None, limit=25, fetch_details=False):
        from jobhunter.connectors.adb.aggregate import aggregate_notice_records

        rows = aggregate_notice_records(_three_expertise_rows("E-990004-001"))
        return AdbCsrnScanResult(records=rows[:limit])

    def map_to_raw_opportunities(self, *args, **kwargs):
        return AdbCsrnConnector().map_to_raw_opportunities(*args, **kwargs)


def test_unaggregated_rows_share_raw_id_and_skip_processing(db_session: Session) -> None:
    """Documents pre-17E-1A defect: identical raw ids short-circuit processing."""
    scan_id = "scan-dup-test-0001"
    retrieved = datetime(2026, 9, 29, tzinfo=timezone.utc)
    processor = OpportunityProcessingService(
        db_session, AdbCsrnOpportunityNormalizer()
    )
    raws = [
        map_adb_notice_to_raw_for_scan(
            row,
            source_id=ADB_CSRN_SOURCE_ID,
            scan_id=scan_id,
            retrieved_at=retrieved,
        )
        for row in _three_expertise_rows("E-990002-001")
    ]
    assert raws[0].id == raws[1].id == raws[2].id
    first = processor.process(raws[0])
    second = processor.process(raws[1])
    observations = OpportunityObservationRepository(db_session).list_for_opportunity(
        first.opportunity.id
    )
    assert len(observations) == 1
    assert second.created_opportunity is False
    assert "GIS Specialist" not in (first.opportunity.description or "")


def test_aggregated_connector_produces_one_raw_with_all_expertise(
    db_session: Session,
) -> None:
    fetch = AdbCsrnScanResult(records=_three_expertise_rows("E-990003-001"))
    mapping = AdbCsrnConnector().map_to_raw_opportunities(
        fetch,
        source_id=ADB_CSRN_SOURCE_ID,
        scan_id="scan-agg-test-01",
        retrieved_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    assert len(mapping.raw_opportunities) == 1
    raw = mapping.raw_opportunities[0]
    assert "GIS Specialist" in (raw.raw_description or "")
    assert "Land Administration Specialist" in (raw.raw_description or "")
    structured = (raw.extra or {}).get("structured_facts") or {}
    assert structured.get("expertise") == sorted(
        [
            "GIS Specialist",
            "Land Administration Specialist",
            "Survey Specialist",
        ],
        key=str.casefold,
    )


def test_scan_service_idempotency_with_duplicate_listing_rows(
    db_session: Session,
) -> None:
    service = AdbScanService(db_session, _DuplicateRowConnector())
    report = service.run_scan(limit=25, apply=True, run_profile_assessment=False)
    assert report.retrieved == 1
    assert report.processed == 1
    assert report.created_opportunities == 1
    opp_id = report.processed_opportunity_ids[0]
    observations = OpportunityObservationRepository(db_session).list_for_opportunity(
        opp_id
    )
    raw = RawOpportunityRepository(db_session).get_by_id(
        observations[0].raw_opportunity_id
    )
    assert raw is not None
    nested = (raw.extra or {}).get("structured_facts") or {}
    assert len(nested.get("expertise") or []) == 3
    structured = OpportunityStructuredFactsLoader(db_session).load_for_opportunity(
        opp_id
    )
    assert len(structured.expertise) == 3
    opportunity = OpportunityRepository(db_session).get_by_id(opp_id)
    assert opportunity is not None
    prompt = build_opportunity_prompt_text(opportunity, structured)
    assert "GIS Specialist" in prompt[OpportunityEvidenceField.EXPERTISE.value]
    digest_a = compute_opportunity_content_digest(opportunity, structured)
    digest_b = compute_opportunity_content_digest(opportunity, structured)
    assert digest_a == digest_b
