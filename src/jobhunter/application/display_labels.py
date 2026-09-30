"""Shared human-readable labels for operator UI (canonical enums unchanged)."""

from __future__ import annotations

from jobhunter.domain.assessment_enums import (
    AlignmentLevel,
    AssessmentStatus,
    EvidenceBasis,
    OverallRelevance,
    SourceDataSufficiency,
)
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.pursuit_enums import PursuitStatus
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.domain.review_enums import ReviewDisposition

_OVERALL_RELEVANCE = {
    OverallRelevance.STRONG_FIT: "Strong fit",
    OverallRelevance.MODERATE_FIT: "Moderate fit",
    OverallRelevance.WEAK_FIT: "Weak fit",
    OverallRelevance.OUT_OF_SCOPE: "Out of scope",
    OverallRelevance.INSUFFICIENT_EVIDENCE: "Insufficient evidence",
    OverallRelevance.UNKNOWN: "Unknown",
}

_SUFFICIENCY = {
    SourceDataSufficiency.LIST_SUMMARY_ONLY: "List summary only",
    SourceDataSufficiency.PARTIAL: "Partial",
    SourceDataSufficiency.ADEQUATE: "Adequate",
}

_ALIGNMENT = {
    AlignmentLevel.STRONG: "Strong",
    AlignmentLevel.MODERATE: "Moderate",
    AlignmentLevel.WEAK: "Weak",
    AlignmentLevel.NONE: "None",
    AlignmentLevel.UNKNOWN: "Unknown",
    AlignmentLevel.INSUFFICIENT_EVIDENCE: "Insufficient evidence",
}

_EVIDENCE_BASIS = {
    EvidenceBasis.OPPORTUNITY_FACT: "Opportunity fact",
    EvidenceBasis.PROFILE_FACT: "Profile fact",
    EvidenceBasis.INFERENCE: "Inference",
}

_ELIGIBILITY = {
    EligibilityStatus.ELIGIBLE: "Eligible",
    EligibilityStatus.INELIGIBLE: "Ineligible",
    EligibilityStatus.REVIEW_REQUIRED: "Review required",
}

_LIFECYCLE = {
    LifecycleStatus.NEW: "New",
    LifecycleStatus.STILL_OPEN: "Still open",
    LifecycleStatus.UPDATED: "Updated",
    LifecycleStatus.CLOSED: "Closed",
    LifecycleStatus.EXPIRED: "Expired",
}

_PRIORITY_BAND = {
    PriorityBand.HIGH: "High",
    PriorityBand.MEDIUM: "Medium",
    PriorityBand.LOW: "Low",
    PriorityBand.REVIEW: "Review",
}

_RANKING_STATUS = {
    RankingStatus.RANKED: "Ranked",
    RankingStatus.UNRANKED: "Unranked",
    RankingStatus.EXCLUDED: "Excluded",
}

_PURSUIT = {
    PursuitStatus.CONSIDERING: "Considering",
    PursuitStatus.PREPARING: "Preparing",
    PursuitStatus.SUBMITTED: "Submitted",
    PursuitStatus.CLIENT_SHORTLISTED: "Client shortlisted",
    PursuitStatus.INTERVIEW: "Interview",
    PursuitStatus.NEGOTIATION: "Negotiation",
    PursuitStatus.AWARDED: "Awarded",
    PursuitStatus.NOT_AWARDED: "Not awarded",
    PursuitStatus.WITHDRAWN: "Withdrawn",
}

_REVIEW = {
    ReviewDisposition.SHORTLIST: "Shortlist",
    ReviewDisposition.INVESTIGATE: "Investigate",
    ReviewDisposition.DISMISS: "Dismiss",
}

_ASSESSMENT_STATUS = {
    AssessmentStatus.SUCCEEDED: "Succeeded",
    AssessmentStatus.SUCCEEDED_WITH_WARNINGS: "Succeeded with warnings",
    AssessmentStatus.FAILED_VALIDATION: "Failed validation",
    AssessmentStatus.FAILED_PROVIDER: "Failed provider",
}


def compact_label_overall_relevance(
    value: str | None,
    *,
    assessment_state: str | None = None,
) -> str:
    """Short relevance label for queue table columns."""
    from jobhunter.application.review.dtos import AssessmentDisplayState

    if assessment_state in (
        AssessmentDisplayState.NONE.value,
        AssessmentDisplayState.FAILED.value,
    ):
        return "Needs review"
    if not value:
        return "Needs review"
    try:
        rel = OverallRelevance(value)
    except ValueError:
        return "Needs review"
    if rel is OverallRelevance.STRONG_FIT:
        return "Strong"
    if rel is OverallRelevance.MODERATE_FIT:
        return "Moderate"
    if rel is OverallRelevance.WEAK_FIT:
        return "Weak"
    if rel is OverallRelevance.OUT_OF_SCOPE:
        return "Out of scope"
    if rel in (OverallRelevance.UNKNOWN, OverallRelevance.INSUFFICIENT_EVIDENCE):
        return "Needs review"
    return label_overall_relevance(value)


def compact_label_source_data_sufficiency(value: str | None) -> str:
    if not value:
        return "—"
    try:
        level = SourceDataSufficiency(value)
    except ValueError:
        return value.replace("_", " ").title()
    if level is SourceDataSufficiency.LIST_SUMMARY_ONLY:
        return "LIST SUMMARY"
    return level.value


def label_overall_relevance(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _OVERALL_RELEVANCE.get(OverallRelevance(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_source_data_sufficiency(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _SUFFICIENCY.get(SourceDataSufficiency(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_alignment(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _ALIGNMENT.get(AlignmentLevel(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_evidence_basis(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _EVIDENCE_BASIS.get(EvidenceBasis(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_eligibility_status(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _ELIGIBILITY.get(EligibilityStatus(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_lifecycle_status(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _LIFECYCLE.get(LifecycleStatus(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_priority_band(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _PRIORITY_BAND.get(PriorityBand(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_ranking_status(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _RANKING_STATUS.get(RankingStatus(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_pursuit_status(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _PURSUIT.get(PursuitStatus(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_review_disposition(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _REVIEW.get(ReviewDisposition(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_assessment_status(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _ASSESSMENT_STATUS.get(AssessmentStatus(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def sufficiency_operator_notice(value: str | None) -> str | None:
    if not value:
        return None
    try:
        level = SourceDataSufficiency(value)
    except ValueError:
        return None
    if level is SourceDataSufficiency.LIST_SUMMARY_ONLY:
        return (
            "Assessment is based on limited source information (listing/summary only). "
            "Some sections may be sparse or empty by design."
        )
    if level is SourceDataSufficiency.PARTIAL:
        return (
            "Assessment was performed with incomplete source information. "
            "Treat detailed alignments with appropriate caution."
        )
    return None
