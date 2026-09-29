"""Regression tests for assessment relevance output and downstream ranking."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from jobhunter.ai.fake_model import FakeAssessmentModel
from jobhunter.application.profile_assessment.service import (
    OpportunityProfileAssessmentService,
)
from jobhunter.application.profile_assessment.validation import (
    AssessmentValidationService,
)
from jobhunter.application.profile_assessment.context_builder import (
    ProfileEvidenceContextBuilder,
)
from jobhunter.application.ranking.service import OpportunityRankingService
from jobhunter.domain.assessment_enums import (
    AssessmentStatus,
    OverallRelevance,
    SourceDataSufficiency,
)
from jobhunter.domain.assessment_request import AssessmentRequest
from jobhunter.domain.assessment_enums import PROFILE_ASSESSMENT_SCHEMA_VERSION
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from tests.application.test_profile_assessment import _catalog

pytestmark = pytest.mark.integration


def _request_for(opp: Opportunity, sufficiency: SourceDataSufficiency) -> AssessmentRequest:
    pack = ProfileEvidenceContextBuilder().build(opp, _catalog(), [])
    return AssessmentRequest(
        schema_version=PROFILE_ASSESSMENT_SCHEMA_VERSION,
        opportunity=opp.to_mapping(),
        opportunity_prompt_text={
            "TITLE": opp.title,
            "DESCRIPTION": opp.description or "",
            "LOCATION": "",
            "ORGANISATION": "",
            "OPPORTUNITY_TYPE": opp.opportunity_type.value,
            "SOURCE_STATUS": "",
            "EXPERTISE": "",
            "SECTORS": "",
        },
        source_data_sufficiency=sufficiency,
        evidence_pack=pack,
        search_themes=[],
        preference_criteria=[],
        eligibility_rule_summaries=[],
    )


def _minimal_valid_payload(overall: str, sufficiency: str, scope: str, rationale: str) -> dict:
    return {
        "overall_relevance": overall,
        "source_data_sufficiency": sufficiency,
        "professional_relevance": {
            "scope_summary": scope,
            "delivery_mode_inference": "UNKNOWN",
            "seniority_inference": "UNKNOWN",
            "domain_tags": [],
        },
        "service_alignments": [],
        "assignment_evidence": [],
        "capability_evidence": [],
        "skill_evidence": [],
        "language_evidence": [],
        "country_evidence": [],
        "theme_alignments": [],
        "preference_notes": [],
        "interpreted_eligibility": [],
        "strengths": [],
        "gaps": [],
        "uncertainties": [],
        "rationale": rationale,
    }


def test_production_style_empty_unknown_fails_validation() -> None:
    opp = Opportunity(
        id="opp-civil",
        title="Civil Engineer",
        description="x" * 500,
    )
    request = _request_for(opp, SourceDataSufficiency.ADEQUATE)
    raw = _minimal_valid_payload(
        OverallRelevance.UNKNOWN.value,
        SourceDataSufficiency.ADEQUATE.value,
        "",
        "",
    )
    outcome = AssessmentValidationService().validate(
        raw, request, allowed_theme_keys=set()
    )
    assert outcome.failed
    assert outcome.result is None


def test_strong_fit_survives_validation_persist_and_ranking(db_session: Session) -> None:
    opp = OpportunityRepository(db_session).save(
        Opportunity(
            id="rel-pipe-strong",
            title="Senior Land Information System implementation consultant",
            description="Cadastral and land registry digitalisation programme.",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    from jobhunter.application.eligibility import EligibilityFilterService

    EligibilityFilterService(db_session).evaluate_and_persist(opp.id)

    model = FakeAssessmentModel()
    outcome = OpportunityProfileAssessmentService(db_session, model).assess_opportunity(
        opp.id, force=True
    )
    assert outcome.assessment is not None
    assert outcome.assessment.status is AssessmentStatus.SUCCEEDED
    assert (
        outcome.assessment.result["overall_relevance"]
        == OverallRelevance.STRONG_FIT.value
    )
    db_session.commit()

    from jobhunter.infrastructure.persistence.assessment_repositories import (
        OpportunityProfileAssessmentRepository,
    )

    reloaded = OpportunityProfileAssessmentRepository(db_session).get_by_id(
        outcome.assessment.id
    )
    assert reloaded is not None
    assert reloaded.result["overall_relevance"] == OverallRelevance.STRONG_FIT.value

    rank_out = OpportunityRankingService(db_session).rank_opportunity(
        opp.id, include_fake_assessments=True
    )
    assert rank_out.ranking is not None
    assert rank_out.ranking.status is RankingStatus.RANKED
    assert rank_out.ranking.priority_band in (
        PriorityBand.HIGH,
        PriorityBand.MEDIUM,
        PriorityBand.LOW,
    )


@pytest.mark.parametrize(
    ("title", "description", "overall", "sufficiency"),
    [
        (
            "National land administration and cadastre modernisation specialist",
            "Land registry and cadastral system implementation.",
            OverallRelevance.STRONG_FIT,
            SourceDataSufficiency.ADEQUATE,
        ),
        (
            "GIS database developer for spatial data infrastructure",
            "PostGIS and enterprise geospatial integration.",
            OverallRelevance.MODERATE_FIT,
            SourceDataSufficiency.ADEQUATE,
        ),
        (
            "Digital transformation programme manager for land agencies",
            "Enterprise architecture for land information systems.",
            OverallRelevance.WEAK_FIT,
            SourceDataSufficiency.ADEQUATE,
        ),
        (
            "Civil Engineer",
            "Structural design and construction supervision.",
            OverallRelevance.OUT_OF_SCOPE,
            SourceDataSufficiency.ADEQUATE,
        ),
        (
            "Health, Safety, Social and Environmental / Safeguard Officer",
            "HSSE compliance on infrastructure works.",
            OverallRelevance.OUT_OF_SCOPE,
            SourceDataSufficiency.ADEQUATE,
        ),
        (
            "Gender and Social Inclusion Specialist",
            "GESI mainstreaming for development programmes.",
            OverallRelevance.OUT_OF_SCOPE,
            SourceDataSufficiency.ADEQUATE,
        ),
        (
            "Consultant",
            "Title only listing.",
            OverallRelevance.INSUFFICIENT_EVIDENCE,
            SourceDataSufficiency.LIST_SUMMARY_ONLY,
        ),
    ],
)
def test_fixture_relevance_classifications_validate(
    title: str,
    description: str,
    overall: OverallRelevance,
    sufficiency: SourceDataSufficiency,
) -> None:
    opp = Opportunity(id="fixture", title=title, description=description)
    request = _request_for(opp, sufficiency)
    raw = _minimal_valid_payload(
        overall.value,
        sufficiency.value,
        f"Scope: {title[:80]}",
        f"Assessment rationale for {overall.value}.",
    )
    outcome = AssessmentValidationService().validate(
        raw, request, allowed_theme_keys=set()
    )
    assert not outcome.failed
    assert outcome.result is not None
    assert outcome.result.overall_relevance is overall
