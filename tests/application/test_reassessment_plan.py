"""Reassessment population planning (integration)."""

from __future__ import annotations

import pytest

from jobhunter.ai.fake_model import FakeAssessmentModel
from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.application.profile_assessment.reassessment_plan import (
    build_reassessment_population,
)
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

pytestmark = pytest.mark.integration


def test_reassessment_plan_counts_actionable_eligible(db_session) -> None:
    from jobhunter.domain.opportunity import Opportunity

    OpportunityRepository(db_session).save(
        Opportunity(
            id="reassess-opp-1",
            title="Land information system consultant",
            description="Cadastre implementation.",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    EligibilityFilterService(db_session).evaluate_and_persist("reassess-opp-1")
    pop = build_reassessment_population(db_session, FakeAssessmentModel())
    assert pop.actionable_eligible >= 1
    ids = {row.opportunity_id for row in pop.rows}
    assert "reassess-opp-1" in ids
