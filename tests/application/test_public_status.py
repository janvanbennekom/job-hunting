"""Public aggregate status page."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.review.dashboard_summary import DashboardSummaryService
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.ui.public_status.html import render_public_status_html

pytestmark = pytest.mark.integration


def test_public_html_uses_dashboard_summary_metrics(db_session: Session) -> None:
    OpportunityRepository(db_session).save(
        Opportunity(
            id="pub-opp-1",
            title="Secret GIS Consultant Title",
            organisation="Secret Client Org",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    summary = DashboardSummaryService(db_session).build_summary(allow_fake=False)
    html = render_public_status_html(summary)
    assert "Secret GIS Consultant Title" not in html
    assert "Secret Client Org" not in html
    assert "pub-opp-1" not in html
    assert str(summary.total_opportunities) in html
    assert "Lifecycle" in html
    assert "Eligibility" in html


def test_public_server_rejects_unknown_paths() -> None:
    from jobhunter.ui.public_status.server import application

    status: list[str] = []
    body = b"".join(
        application(
            {"PATH_INFO": "/app/opportunities"},
            lambda code, headers: status.append(code),
        )
    )
    assert status[0].startswith("404")
    assert body == b"Not Found"
