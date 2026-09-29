"""Source link listing vs application URL from structured_facts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.opportunity_processing import OpportunityProcessingService
from jobhunter.connectors.developmentaid.normalizer import DevelopmentAidOpportunityNormalizer
from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_SOURCE_ID
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.infrastructure.persistence.repositories import OpportunitySourceRepository

pytestmark = pytest.mark.integration


def test_listing_and_application_urls_stored_separately(db_session: Session) -> None:
    listing = "https://www.developmentaid.org/jobs/view/991122/view-slug"
    application = "https://employer.example.org/apply/991122"
    raw = RawOpportunity(
        id="raw-da-link-test",
        source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
        source_reference="991122",
        source_url=listing,
        retrieved_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
        raw_title="Link test role",
        raw_description="Sufficient description for normalization.",
        extra={
            "structured_facts": {
                "application_url": application,
            }
        },
    )
    result = OpportunityProcessingService(
        db_session, DevelopmentAidOpportunityNormalizer()
    ).process(raw)
    links = OpportunitySourceRepository(db_session).list_for_opportunity(
        result.opportunity.id
    )
    assert len(links) == 1
    link = links[0]
    assert link.source_url == listing
    assert link.original_url == application
