"""Tests for Phase 8 profile/relevance assessment."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from jobhunter.ai.fake_model import FakeAssessmentModel
from jobhunter.application.profile_assessment.context_builder import (
    ProfileEvidenceContextBuilder,
)
from jobhunter.application.profile_assessment.digests import (
    compute_input_digest,
    compute_opportunity_content_digest,
)
from jobhunter.application.profile_assessment.evidence_loader import (
    ProfessionalEvidenceCatalog,
    ProfessionalEvidenceLoader,
)
from jobhunter.application.profile_assessment.service import (
    OpportunityProfileAssessmentService,
)
from jobhunter.application.profile_assessment.source_sufficiency import (
    infer_source_data_sufficiency,
)
from jobhunter.application.profile_assessment.validation import (
    AssessmentValidationService,
)
from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID
from jobhunter.domain.assessment_enums import (
    AlignmentLevel,
    AssessmentStatus,
    EvidenceBasis,
    OverallRelevance,
    SourceDataSufficiency,
)
from jobhunter.domain.assessment_request import AssessmentRequest
from jobhunter.domain.assignment import Assignment
from jobhunter.domain.capability import Capability
from jobhunter.domain.country_experience import CountryExperience
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.evidence_context_pack import EvidenceContextPack
from jobhunter.domain.language_capability import LanguageCapability
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.professional_profile import ProfessionalProfile
from jobhunter.domain.professional_service import ProfessionalService
from jobhunter.domain.profile_enums import CapabilityCategory
from jobhunter.domain.skill import Skill
from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

pytestmark_integration = pytest.mark.integration


def _catalog() -> ProfessionalEvidenceCatalog:
    profile = ProfessionalProfile(
        id="profile-1",
        display_name="Jan",
        positioning_summary="Senior Geo-ICT specialist.",
    )
    service = ProfessionalService(id="svc-1", name="LIS Implementation")
    assignment = Assignment(
        id="asg-1",
        project_name="National LIS rollout",
        country="Kenya",
        description="Land information system implementation",
    )
    return ProfessionalEvidenceCatalog(
        profile=profile,
        services=[service],
        assignments=[assignment],
        capabilities=[
            Capability(
                id="cap-1",
                code="lis",
                name="Land Information Systems",
                category=CapabilityCategory.DOMAIN,
            )
        ],
        skills=[Skill(id="skill-1", name="PostGIS")],
        languages=[LanguageCapability(id="lang-1", language="English")],
        countries=[CountryExperience(id="cty-1", country="Kenya")],
    )


def test_strong_lis_match_via_fake_model() -> None:
    opp = Opportunity(
        id="opp-lis",
        title="Senior Land Information System consultant",
        description="Implementation of cadastral workflows.",
    )
    pack = ProfileEvidenceContextBuilder().build(opp, _catalog(), [])
    request = AssessmentRequest(
        schema_version="profile_assessment_v1",
        opportunity=opp.to_mapping(),
        opportunity_prompt_text={
            "TITLE": opp.title,
            "DESCRIPTION": opp.description or "",
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
    response = FakeAssessmentModel().assess(request)
    assert response.parsed is not None
    assert response.parsed["overall_relevance"] == OverallRelevance.STRONG_FIT.value
    validation = AssessmentValidationService().validate(
        response.parsed, request, allowed_theme_keys=set()
    )
    assert validation.result is not None
    assert validation.result.service_alignments


def test_weak_unrelated_opportunity() -> None:
    opp = Opportunity(id="opp-weak", title="Unrelated marketing coordinator")
    pack = ProfileEvidenceContextBuilder().build(opp, _catalog(), [])
    request = AssessmentRequest(
        schema_version="profile_assessment_v1",
        opportunity=opp.to_mapping(),
        opportunity_prompt_text={"TITLE": opp.title, "DESCRIPTION": ""},
        source_data_sufficiency=SourceDataSufficiency.PARTIAL,
        evidence_pack=pack,
        search_themes=[],
        preference_criteria=[],
        eligibility_rule_summaries=[],
    )
    parsed = FakeAssessmentModel().assess(request).parsed
    assert parsed is not None
    assert parsed["overall_relevance"] == OverallRelevance.OUT_OF_SCOPE.value


def test_sparse_fao_source_sufficiency() -> None:
    opp = Opportunity(
        title="Consultant",
        description="Title: X\nOpportunity category: Consultancy",
    )
    suff = infer_source_data_sufficiency(
        opp, primary_source_id=FAO_JOBS_SOURCE_ID
    )
    assert suff is SourceDataSufficiency.LIST_SUMMARY_ONLY


def test_reject_hallucinated_profile_id() -> None:
    opp = Opportunity(id="opp-h", title="GIS")
    pack = ProfileEvidenceContextBuilder().build(opp, _catalog(), [])
    request = AssessmentRequest(
        schema_version="profile_assessment_v1",
        opportunity=opp.to_mapping(),
        opportunity_prompt_text={"TITLE": opp.title, "DESCRIPTION": ""},
        source_data_sufficiency=SourceDataSufficiency.ADEQUATE,
        evidence_pack=pack,
        search_themes=[],
        preference_criteria=[],
        eligibility_rule_summaries=[],
    )
    raw = {
        "overall_relevance": OverallRelevance.STRONG_FIT.value,
        "source_data_sufficiency": SourceDataSufficiency.ADEQUATE.value,
        "professional_relevance": {
            "scope_summary": "x",
            "delivery_mode_inference": "UNKNOWN",
            "seniority_inference": "UNKNOWN",
            "domain_tags": [],
        },
        "assignment_evidence": [
            {
                "entity_id": "missing-assignment",
                "alignment": AlignmentLevel.STRONG.value,
                "basis": EvidenceBasis.PROFILE_FACT.value,
                "rationale": "bad",
                "opportunity_refs": [],
            }
        ],
        "service_alignments": [],
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
        "rationale": "",
    }
    outcome = AssessmentValidationService().validate(
        raw, request, allowed_theme_keys=set()
    )
    assert outcome.result is not None
    assert outcome.result.assignment_evidence == []
    assert any("rejected unknown" in w for w in outcome.warnings)


def test_invalid_opportunity_excerpt_rejected() -> None:
    opp = Opportunity(id="opp-ex", title="Land administration")
    pack = ProfileEvidenceContextBuilder().build(opp, _catalog(), [])
    request = AssessmentRequest(
        schema_version="profile_assessment_v1",
        opportunity=opp.to_mapping(),
        opportunity_prompt_text={"TITLE": opp.title, "DESCRIPTION": ""},
        source_data_sufficiency=SourceDataSufficiency.ADEQUATE,
        evidence_pack=pack,
        search_themes=[],
        preference_criteria=[],
        eligibility_rule_summaries=[],
    )
    raw = FakeAssessmentModel().assess(request).parsed
    assert raw is not None
    raw["service_alignments"] = [
        {
            "professional_service_id": "svc-1",
            "alignment": AlignmentLevel.STRONG.value,
            "basis": EvidenceBasis.INFERENCE.value,
            "rationale": "x",
            "opportunity_refs": [
                {"field": "TITLE", "excerpt": "nonexistent substring"}
            ],
        }
    ]
    outcome = AssessmentValidationService().validate(
        raw, request, allowed_theme_keys=set()
    )
    assert outcome.result is not None
    assert all(
        not alignment.opportunity_refs
        for alignment in outcome.result.service_alignments
    )


def test_malformed_model_output_fails_validation() -> None:
    opp = Opportunity(id="opp-mal", title="GIS")
    pack = ProfileEvidenceContextBuilder().build(opp, _catalog(), [])
    request = AssessmentRequest(
        schema_version="profile_assessment_v1",
        opportunity=opp.to_mapping(),
        opportunity_prompt_text={"TITLE": opp.title, "DESCRIPTION": ""},
        source_data_sufficiency=SourceDataSufficiency.ADEQUATE,
        evidence_pack=pack,
        search_themes=[],
        preference_criteria=[],
        eligibility_rule_summaries=[],
    )
    outcome = AssessmentValidationService().validate(
        {"overall_relevance": "NOT_A_REAL_VALUE"},
        request,
        allowed_theme_keys=set(),
    )
    assert outcome.failed


@pytest.mark.integration
def test_provider_failure_persisted(db_session: Session) -> None:
    pytest.importorskip("sqlalchemy")
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="assess-fail-provider-001",
            title="Land administration consultant",
            lifecycle_status=LifecycleStatus.NEW,
        )
    )
    EligibilityFilterService(db_session).evaluate_and_persist(opp.id)
    model = FakeAssessmentModel(raise_provider_error=True)
    try:
        loader = ProfessionalEvidenceLoader(db_session)
        loader.load_primary()
    except RuntimeError:
        pytest.skip("Primary professional profile not loaded in database")
    service = OpportunityProfileAssessmentService(db_session, model)
    outcome = service.assess_opportunity(opp.id)
    assert outcome.assessment is not None
    assert outcome.assessment.status is AssessmentStatus.FAILED_PROVIDER


@pytest.mark.integration
def test_ineligible_gating(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="assess-ineligible-001",
            title="Internship programme assistant",
            description="Internship programme for graduates.",
            lifecycle_status=LifecycleStatus.NEW,
        )
    )
    EligibilityFilterService(db_session).evaluate_and_persist(opp.id)
    try:
        ProfessionalEvidenceLoader(db_session).load_primary()
    except RuntimeError:
        pytest.skip("Primary professional profile not loaded in database")
    service = OpportunityProfileAssessmentService(
        db_session, FakeAssessmentModel()
    )
    outcome = service.assess_opportunity(opp.id)
    assert outcome.skipped
    assert outcome.skip_reason == "ineligible_gated"


@pytest.mark.integration
def test_assessment_reuse_idempotency(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="assess-reuse-001",
            title="Senior Land Information System consultant",
            description="LIS implementation support.",
            lifecycle_status=LifecycleStatus.NEW,
        )
    )
    EligibilityFilterService(db_session).evaluate_and_persist(opp.id)
    try:
        ProfessionalEvidenceLoader(db_session).load_primary()
    except RuntimeError:
        pytest.skip("Primary professional profile not loaded in database")
    model = FakeAssessmentModel()
    service = OpportunityProfileAssessmentService(db_session, model)
    first = service.assess_opportunity(opp.id)
    second = service.assess_opportunity(opp.id)
    assert first.assessment is not None
    assert second.reused
    assert second.assessment is not None
    assert first.assessment.id == second.assessment.id
    assert model.call_count == 1


@pytest.mark.integration
def test_material_change_triggers_new_assessment(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="assess-change-001",
            title="GIS consultant",
            description="Initial description.",
            lifecycle_status=LifecycleStatus.NEW,
        )
    )
    EligibilityFilterService(db_session).evaluate_and_persist(opp.id)
    try:
        ProfessionalEvidenceLoader(db_session).load_primary()
    except RuntimeError:
        pytest.skip("Primary professional profile not loaded in database")
    model = FakeAssessmentModel()
    service = OpportunityProfileAssessmentService(db_session, model)
    first = service.assess_opportunity(opp.id)
    updated = Opportunity(
        id=opp.id,
        title=opp.title,
        description="Materially changed description with new scope.",
        lifecycle_status=opp.lifecycle_status,
        eligibility_status=opp.eligibility_status,
        canonical_identity_key=opp.canonical_identity_key,
        source_status=opp.source_status,
    )
    opportunities.save(updated)
    second = service.assess_opportunity(opp.id, force=True)
    assert first.assessment is not None
    assert second.assessment is not None
    assert first.assessment.id != second.assessment.id


def test_input_digest_changes_with_model_name() -> None:
    base = compute_input_digest(
        opportunity_content_digest="a" * 64,
        profile_evidence_digest="b" * 64,
        search_strategy_revision_id="rev-1",
        prompt_schema_version="profile_assessment_v1",
        model_provider="fake",
        model_name="fake-assessment-v1",
    )
    other = compute_input_digest(
        opportunity_content_digest="a" * 64,
        profile_evidence_digest="b" * 64,
        search_strategy_revision_id="rev-1",
        prompt_schema_version="profile_assessment_v1",
        model_provider="fake",
        model_name="fake-assessment-v2",
    )
    assert base != other


def test_opportunity_content_digest_uses_full_description() -> None:
    long_desc = "x" * 20_000
    opp = Opportunity(title="T", description=long_desc)
    digest = compute_opportunity_content_digest(opp)
    assert digest
    assert len(digest) == 64
