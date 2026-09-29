"""Assessment operator presentation (Phase 16)."""

from __future__ import annotations

from jobhunter.application.review.assessment_presentation import (
    AssessmentOperatorSituation,
    build_assessment_operator_presentation,
    classify_assessment_situation,
)
from jobhunter.application.review.dtos import AssessmentDisplayState
from jobhunter.domain.enums import EligibilityStatus


def test_classify_fake_only() -> None:
    situation = classify_assessment_situation(
        display_state=AssessmentDisplayState.FAKE_ONLY,
        present=False,
        is_fake=False,
        eligibility_status=EligibilityStatus.ELIGIBLE,
    )
    assert situation is AssessmentOperatorSituation.FAKE_ONLY


def test_classify_not_assessed_ineligible() -> None:
    situation = classify_assessment_situation(
        display_state=AssessmentDisplayState.NONE,
        present=False,
        is_fake=False,
        eligibility_status=EligibilityStatus.INELIGIBLE,
    )
    assert situation is AssessmentOperatorSituation.NOT_ASSESSED_INELIGIBLE


def test_structured_presentation_sparse_sections() -> None:
    presentation = build_assessment_operator_presentation(
        display_state=AssessmentDisplayState.PRODUCTION,
        present=True,
        is_fake=False,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        explanation=None,
        result={
            "overall_relevance": "MODERATE_FIT",
            "source_data_sufficiency": "LIST_SUMMARY_ONLY",
            "professional_relevance": {
                "scope_summary": "Limited listing text.",
                "delivery_mode_inference": "UNKNOWN",
                "seniority_inference": "UNKNOWN",
                "domain_tags": [],
            },
            "service_alignments": [],
            "theme_alignments": [],
            "strengths": [],
            "gaps": [],
            "uncertainties": ["Deadline unclear"],
        },
        profile_labels={},
        status="SUCCEEDED",
    )
    assert presentation.show_raw_json
    assert presentation.structured is not None
    assert presentation.structured.strengths == ()
    assert presentation.sufficiency_notice is not None
    assert "limited source" in presentation.sufficiency_notice.lower()


def test_no_payload_hides_raw_json() -> None:
    presentation = build_assessment_operator_presentation(
        display_state=AssessmentDisplayState.NONE,
        present=False,
        is_fake=False,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        explanation="No assessment",
        result=None,
        profile_labels={},
        status=None,
    )
    assert not presentation.show_raw_json
    assert presentation.structured is None
