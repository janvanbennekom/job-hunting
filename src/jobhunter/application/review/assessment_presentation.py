"""Operator-facing assessment presentation from persisted result JSON."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from jobhunter.application.display_labels import (
    label_alignment,
    label_assessment_status,
    label_evidence_basis,
    label_overall_relevance,
    label_source_data_sufficiency,
    sufficiency_operator_notice,
)
from jobhunter.application.review.dtos import AssessmentDisplayState
from jobhunter.domain.enums import EligibilityStatus


class AssessmentOperatorSituation(StrEnum):
    """Why the operator sees the current assessment block."""

    PRODUCTION_SUCCESS = "PRODUCTION_SUCCESS"
    FAKE_VISIBLE = "FAKE_VISIBLE"
    NO_ASSESSMENT = "NO_ASSESSMENT"
    FAKE_ONLY = "FAKE_ONLY"
    FAILED = "FAILED"
    NOT_ASSESSED_INELIGIBLE = "NOT_ASSESSED_INELIGIBLE"
    NOT_ASSESSED_OTHER = "NOT_ASSESSED_OTHER"


@dataclass(frozen=True, slots=True)
class ServiceAlignmentRow:
    service_label: str
    alignment: str
    basis: str
    rationale: str


@dataclass(frozen=True, slots=True)
class ThemeAlignmentRow:
    theme_key: str
    alignment: str
    basis: str
    rationale: str


@dataclass(frozen=True, slots=True)
class EvidenceRow:
    evidence_type: str
    entity_label: str
    alignment: str
    basis: str
    rationale: str


@dataclass(frozen=True, slots=True)
class AssessmentStructuredPresentation:
    overall_relevance: str
    source_data_sufficiency: str
    scope_summary: str
    delivery_mode_inference: str
    seniority_inference: str
    domain_tags: tuple[str, ...]
    service_alignments: tuple[ServiceAlignmentRow, ...]
    theme_alignments: tuple[ThemeAlignmentRow, ...]
    strengths: tuple[str, ...]
    gaps: tuple[str, ...]
    uncertainties: tuple[str, ...]
    evidence_rows: tuple[EvidenceRow, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class AssessmentOperatorPresentation:
    situation: AssessmentOperatorSituation
    headline: str
    detail: str | None
    sufficiency_notice: str | None
    show_raw_json: bool
    structured: AssessmentStructuredPresentation | None


def classify_assessment_situation(
    *,
    display_state: AssessmentDisplayState,
    present: bool,
    is_fake: bool,
    eligibility_status: EligibilityStatus,
) -> AssessmentOperatorSituation:
    if present and is_fake:
        return AssessmentOperatorSituation.FAKE_VISIBLE
    if present:
        return AssessmentOperatorSituation.PRODUCTION_SUCCESS
    if display_state is AssessmentDisplayState.FAILED:
        return AssessmentOperatorSituation.FAILED
    if display_state is AssessmentDisplayState.FAKE_ONLY:
        return AssessmentOperatorSituation.FAKE_ONLY
    if display_state is AssessmentDisplayState.NONE:
        if eligibility_status is EligibilityStatus.INELIGIBLE:
            return AssessmentOperatorSituation.NOT_ASSESSED_INELIGIBLE
        return AssessmentOperatorSituation.NOT_ASSESSED_OTHER
    return AssessmentOperatorSituation.NO_ASSESSMENT


def _headline_for_situation(situation: AssessmentOperatorSituation) -> str:
    return {
        AssessmentOperatorSituation.PRODUCTION_SUCCESS: "Production profile assessment",
        AssessmentOperatorSituation.FAKE_VISIBLE: "Development/fake assessment (not production)",
        AssessmentOperatorSituation.NO_ASSESSMENT: "No profile assessment",
        AssessmentOperatorSituation.FAKE_ONLY: "No production assessment",
        AssessmentOperatorSituation.FAILED: "Assessment attempt failed",
        AssessmentOperatorSituation.NOT_ASSESSED_INELIGIBLE: (
            "Not assessed (ineligible under deterministic rules)"
        ),
        AssessmentOperatorSituation.NOT_ASSESSED_OTHER: "Not assessed yet",
    }[situation]


def _detail_for_situation(
    situation: AssessmentOperatorSituation,
    explanation: str | None,
) -> str | None:
    if explanation:
        return explanation
    if situation is AssessmentOperatorSituation.FAKE_ONLY:
        return (
            "Only development/fake assessments exist for this opportunity. "
            "Run the production assessment pipeline to store an OpenAI result."
        )
    if situation is AssessmentOperatorSituation.NOT_ASSESSED_INELIGIBLE:
        return (
            "Profile assessment is not run for opportunities gated as ineligible "
            "unless explicitly forced in batch tooling."
        )
    if situation is AssessmentOperatorSituation.NOT_ASSESSED_OTHER:
        return (
            "This opportunity has not yet received a successful profile assessment "
            "for the active search strategy revision."
        )
    if situation is AssessmentOperatorSituation.NO_ASSESSMENT:
        return "No assessment record is available."
    return None


def build_assessment_operator_presentation(
    *,
    display_state: AssessmentDisplayState,
    present: bool,
    is_fake: bool,
    eligibility_status: EligibilityStatus,
    explanation: str | None,
    result: dict[str, Any] | None,
    profile_labels: dict[str, str],
    status: str | None,
) -> AssessmentOperatorPresentation:
    situation = classify_assessment_situation(
        display_state=display_state,
        present=present,
        is_fake=is_fake,
        eligibility_status=eligibility_status,
    )
    sufficiency_raw = (result or {}).get("source_data_sufficiency")
    sufficiency_notice = sufficiency_operator_notice(
        str(sufficiency_raw) if sufficiency_raw else None
    )
    structured = (
        _build_structured(result, profile_labels) if present and result else None
    )
    show_raw = bool(present and result)
    detail = _detail_for_situation(situation, explanation)
    if present and status:
        detail = (detail or "") + f" Status: {label_assessment_status(status)}."
    return AssessmentOperatorPresentation(
        situation=situation,
        headline=_headline_for_situation(situation),
        detail=detail.strip() if detail else None,
        sufficiency_notice=sufficiency_notice,
        show_raw_json=show_raw,
        structured=structured,
    )


def _build_structured(
    result: dict[str, Any],
    profile_labels: dict[str, str],
) -> AssessmentStructuredPresentation:
    prof = result.get("professional_relevance") or {}
    service_rows = tuple(
        ServiceAlignmentRow(
            service_label=profile_labels.get(
                str(item.get("professional_service_id", "")),
                str(item.get("professional_service_id", "—")),
            ),
            alignment=label_alignment(str(item.get("alignment", ""))),
            basis=label_evidence_basis(str(item.get("basis", ""))),
            rationale=str(item.get("rationale") or ""),
        )
        for item in (result.get("service_alignments") or [])
        if isinstance(item, dict)
    )
    theme_rows = tuple(
        ThemeAlignmentRow(
            theme_key=str(item.get("theme_key", "")),
            alignment=label_alignment(str(item.get("alignment", ""))),
            basis=label_evidence_basis(str(item.get("basis", ""))),
            rationale=str(item.get("rationale") or ""),
        )
        for item in (result.get("theme_alignments") or [])
        if isinstance(item, dict)
    )
    evidence_rows: list[EvidenceRow] = []
    for label, key in (
        ("Assignment", "assignment_evidence"),
        ("Capability", "capability_evidence"),
        ("Skill", "skill_evidence"),
        ("Language", "language_evidence"),
        ("Country", "country_evidence"),
    ):
        for item in result.get(key) or []:
            if not isinstance(item, dict):
                continue
            entity_id = str(item.get("entity_id", ""))
            evidence_rows.append(
                EvidenceRow(
                    evidence_type=label,
                    entity_label=profile_labels.get(entity_id, entity_id or "—"),
                    alignment=label_alignment(str(item.get("alignment", ""))),
                    basis=label_evidence_basis(str(item.get("basis", ""))),
                    rationale=str(item.get("rationale") or ""),
                )
            )
    strengths = tuple(
        str(s) for s in (result.get("strengths") or []) if str(s).strip()
    )
    gaps = tuple(str(g) for g in (result.get("gaps") or []) if str(g).strip())
    uncertainties = tuple(
        str(u) for u in (result.get("uncertainties") or []) if str(u).strip()
    )
    tags = tuple(
        str(t) for t in (prof.get("domain_tags") or []) if str(t).strip()
    )
    return AssessmentStructuredPresentation(
        overall_relevance=label_overall_relevance(
            str(result.get("overall_relevance", ""))
        ),
        source_data_sufficiency=label_source_data_sufficiency(
            str(result.get("source_data_sufficiency", ""))
        ),
        scope_summary=str(prof.get("scope_summary") or ""),
        delivery_mode_inference=str(prof.get("delivery_mode_inference") or "—"),
        seniority_inference=str(prof.get("seniority_inference") or "—"),
        domain_tags=tags,
        service_alignments=service_rows,
        theme_alignments=theme_rows,
        strengths=strengths,
        gaps=gaps,
        uncertainties=uncertainties,
        evidence_rows=tuple(evidence_rows),
        rationale=str(result.get("rationale") or ""),
    )
