"""Model assessment payload selection and size (no OpenAI)."""

from __future__ import annotations

import json

import pytest

from jobhunter.application.profile_assessment.context_builder import (
    ProfileEvidenceContextBuilder,
)
from jobhunter.application.profile_assessment.model_payload import (
    evidence_pack_to_model_mapping,
)
from jobhunter.application.profile_assessment.payload_metrics import (
    measure_model_request,
)
from jobhunter.domain.assessment_enums import SourceDataSufficiency
from jobhunter.domain.assessment_request import AssessmentRequest
from jobhunter.domain.opportunity import Opportunity
from tests.application.test_profile_assessment import _catalog

pytestmark = pytest.mark.integration


def _build_request(title: str, description: str) -> AssessmentRequest:
    opp = Opportunity(id="fixture", title=title, description=description)
    pack = ProfileEvidenceContextBuilder().build(opp, _catalog(), [])
    return AssessmentRequest(
        schema_version="profile_assessment_v4",
        opportunity=opp.to_mapping(),
        opportunity_prompt_text={
            "TITLE": title,
            "DESCRIPTION": description,
            "LOCATION": "",
            "ORGANISATION": "",
            "OPPORTUNITY_TYPE": opp.opportunity_type.value,
            "SOURCE_STATUS": "",
        },
        source_data_sufficiency=SourceDataSufficiency.ADEQUATE,
        evidence_pack=pack,
        search_themes=[],
        preference_criteria=[],
        eligibility_rule_summaries=[],
    )


def test_model_payload_excludes_selection_notes() -> None:
    request = _build_request("GIS consultant", "Spatial data work.")
    model_pack = request.to_model_mapping()["evidence_pack"]
    assert "selection_notes" not in model_pack


def test_model_payload_excludes_duplicate_opportunity() -> None:
    request = _build_request("GIS consultant", "Spatial data work.")
    payload = request.to_model_mapping()
    assert "opportunity" not in payload
    assert "opportunity_prompt_text" in payload


def test_service_and_assignment_counts() -> None:
    request = _build_request(
        "Senior Land Information System implementation specialist",
        "Cadastre and registry programme.",
    )
    pack = request.to_model_mapping()["evidence_pack"]
    assert len(pack["professional_services"]) <= 4
    assert len(pack["assignments"]) <= 5


@pytest.mark.parametrize(
    ("title", "description", "expect_assignment_keyword"),
    [
        (
            "National land administration and cadastre modernisation specialist",
            "Land registry implementation.",
            "land",
        ),
        (
            "GIS database developer for spatial data infrastructure",
            "PostGIS enterprise SDI.",
            "gis",
        ),
        (
            "Digital transformation programme manager for land agencies",
            "Enterprise architecture interoperability.",
            "digital",
        ),
        (
            "Civil Engineer",
            "Structural design.",
            None,
        ),
        (
            "Health, Safety, Social and Environmental / Safeguard Officer",
            "HSSE compliance.",
            None,
        ),
        (
            "Gender and Social Inclusion Specialist",
            "GESI mainstreaming.",
            None,
        ),
        (
            "Consultant",
            "Title only listing.",
            None,
        ),
    ],
)
def test_regression_fixture_evidence_selection(
    title: str,
    description: str,
    expect_assignment_keyword: str | None,
) -> None:
    request = _build_request(title, description)
    pack = request.to_model_mapping()["evidence_pack"]
    assignment_blob = json.dumps(pack["assignments"]).lower()
    if title.lower().find("land") >= 0 or "lis" in title.lower():
        assert pack["assignments"], "expected at least one assignment for land/LIS role"
    if expect_assignment_keyword == "land":
        assert "land" in assignment_blob or "cadast" in assignment_blob
    if expect_assignment_keyword == "gis":
        service_blob = json.dumps(pack["professional_services"]).lower()
        assert (
            "gis" in assignment_blob
            or "geospatial" in assignment_blob
            or "gis" in service_blob
            or "land information" in assignment_blob
        )
    if expect_assignment_keyword == "digital":
        assert pack["assignments"]


def test_token_usage_persisted_on_success(db_session) -> None:
    from jobhunter.ai.fake_model import FakeAssessmentModel
    from jobhunter.application.eligibility import EligibilityFilterService
    from jobhunter.application.profile_assessment.service import (
        OpportunityProfileAssessmentService,
    )
    from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

    opp = OpportunityRepository(db_session).save(
        Opportunity(
            id="usage-opp-1",
            title="Land information system consultant",
            description="LIS rollout.",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    EligibilityFilterService(db_session).evaluate_and_persist(opp.id)

    class _UsageFake(FakeAssessmentModel):
        def assess(self, request):  # noqa: ANN001
            response = super().assess(request)
            response.usage = {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
            return response

    outcome = OpportunityProfileAssessmentService(
        db_session, _UsageFake()
    ).assess_opportunity(opp.id, force=True)
    assert outcome.assessment is not None
    assert outcome.assessment.prompt_tokens == 100
    assert outcome.assessment.completion_tokens == 50
    assert outcome.assessment.total_tokens == 150


def test_median_payload_below_legacy_threshold() -> None:
    """Smoke: optimized civil-engineer fixture should be well below pre-17G-1A size."""
    request = _build_request("Civil Engineer", "x" * 500)
    metrics = measure_model_request(request)
    assert metrics.estimated_input_tokens < 8000
