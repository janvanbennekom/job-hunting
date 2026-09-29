"""Validate and ground AI assessment structured output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jobhunter.domain.assessment_enums import (
    AlignmentLevel,
    EvidenceBasis,
    OpportunityEvidenceField,
    OverallRelevance,
    SourceDataSufficiency,
)
from jobhunter.domain.assessment_result import (
    AssessmentResult,
    EntityEvidence,
    InterpretedEligibilityNote,
    OpportunityEvidenceRef,
    PreferenceNote,
    ProfessionalRelevanceSection,
    ServiceAlignment,
    ThemeAlignment,
)
from jobhunter.domain.assessment_request import AssessmentRequest
from jobhunter.domain.evidence_context_pack import EvidenceContextPack


@dataclass(slots=True)
class ValidationOutcome:
    result: AssessmentResult | None
    warnings: list[str]
    failed: bool


class AssessmentValidationService:
    @staticmethod
    def _opportunity_text_volume(opportunity_fields: dict[str, str]) -> int:
        parts = (
            opportunity_fields.get("TITLE") or "",
            opportunity_fields.get("DESCRIPTION") or "",
            opportunity_fields.get("EXPERTISE") or "",
            opportunity_fields.get("SECTORS") or "",
        )
        return sum(len(part.strip()) for part in parts)

    def _reject_empty_unknown_relevance(
        self,
        raw: dict[str, Any],
        overall: OverallRelevance,
        request: AssessmentRequest,
        opportunity_fields: dict[str, str],
        warnings: list[str],
    ) -> ValidationOutcome | None:
        if overall is not OverallRelevance.UNKNOWN:
            return None
        try:
            sufficiency = SourceDataSufficiency(
                str(
                    raw.get(
                        "source_data_sufficiency",
                        request.source_data_sufficiency.value,
                    )
                )
            )
        except ValueError:
            sufficiency = request.source_data_sufficiency
        if sufficiency is SourceDataSufficiency.LIST_SUMMARY_ONLY:
            return None
        if self._opportunity_text_volume(opportunity_fields) < 200:
            return None
        prof_raw = raw.get("professional_relevance") or {}
        scope = str(prof_raw.get("scope_summary", "")).strip()
        rationale = str(raw.get("rationale", "")).strip()
        if scope or rationale:
            return None
        warnings.append(
            "UNKNOWN overall_relevance with adequate opportunity text but empty "
            "professional_relevance.scope_summary and rationale"
        )
        return ValidationOutcome(None, warnings, True)

    def validate(
        self,
        raw: dict[str, Any],
        request: AssessmentRequest,
        *,
        allowed_theme_keys: set[str],
    ) -> ValidationOutcome:
        warnings: list[str] = []
        pack = request.evidence_pack
        allowed_ids = pack.allowed_profile_ids()
        opportunity_fields = request.opportunity_prompt_text

        try:
            overall = OverallRelevance(str(raw.get("overall_relevance", "UNKNOWN")))
        except ValueError:
            return ValidationOutcome(None, ["invalid overall_relevance"], True)

        narrative_failure = self._reject_empty_unknown_relevance(
            raw, overall, request, opportunity_fields, warnings
        )
        if narrative_failure:
            return narrative_failure

        try:
            sufficiency = SourceDataSufficiency(
                str(
                    raw.get(
                        "source_data_sufficiency",
                        request.source_data_sufficiency.value,
                    )
                )
            )
        except ValueError:
            warnings.append("invalid source_data_sufficiency; using request default")
            sufficiency = request.source_data_sufficiency

        prof_raw = raw.get("professional_relevance") or {}
        professional_relevance = ProfessionalRelevanceSection(
            scope_summary=str(prof_raw.get("scope_summary", "")),
            delivery_mode_inference=str(
                prof_raw.get("delivery_mode_inference", "UNKNOWN")
            ),
            seniority_inference=str(prof_raw.get("seniority_inference", "UNKNOWN")),
            domain_tags=[
                str(tag) for tag in (prof_raw.get("domain_tags") or [])
            ],
        )

        service_alignments = self._parse_service_alignments(
            raw.get("service_alignments") or [],
            allowed_ids,
            opportunity_fields,
            warnings,
        )
        assignment_evidence = self._parse_entity_evidence(
            raw.get("assignment_evidence") or [],
            allowed_ids,
            opportunity_fields,
            warnings,
            label="assignment",
        )
        capability_evidence = self._parse_entity_evidence(
            raw.get("capability_evidence") or [],
            allowed_ids,
            opportunity_fields,
            warnings,
            label="capability",
        )
        skill_evidence = self._parse_entity_evidence(
            raw.get("skill_evidence") or [],
            allowed_ids,
            opportunity_fields,
            warnings,
            label="skill",
        )
        language_evidence = self._parse_entity_evidence(
            raw.get("language_evidence") or [],
            allowed_ids,
            opportunity_fields,
            warnings,
            label="language",
        )
        country_evidence = self._parse_entity_evidence(
            raw.get("country_evidence") or [],
            allowed_ids,
            opportunity_fields,
            warnings,
            label="country",
        )
        theme_alignments = self._parse_theme_alignments(
            raw.get("theme_alignments") or [],
            allowed_theme_keys,
            warnings,
        )
        preference_notes = self._parse_preference_notes(
            raw.get("preference_notes") or [], warnings
        )
        interpreted_eligibility = self._parse_interpreted_eligibility(
            raw.get("interpreted_eligibility") or [], warnings
        )

        strengths = [str(s) for s in (raw.get("strengths") or [])]
        gaps = [str(g) for g in (raw.get("gaps") or [])]
        uncertainties = [str(u) for u in (raw.get("uncertainties") or [])]
        rationale = str(raw.get("rationale", ""))

        grounded_count = (
            len(service_alignments)
            + len(assignment_evidence)
            + len(capability_evidence)
            + len(skill_evidence)
        )
        if overall in (OverallRelevance.STRONG_FIT, OverallRelevance.MODERATE_FIT):
            if grounded_count == 0 and sufficiency != SourceDataSufficiency.ADEQUATE:
                warnings.append(
                    "strong/moderate relevance without grounded profile evidence"
                )
                overall = OverallRelevance.INSUFFICIENT_EVIDENCE

        result = AssessmentResult(
            overall_relevance=overall,
            source_data_sufficiency=sufficiency,
            professional_relevance=professional_relevance,
            service_alignments=service_alignments,
            assignment_evidence=assignment_evidence,
            capability_evidence=capability_evidence,
            skill_evidence=skill_evidence,
            language_evidence=language_evidence,
            country_evidence=country_evidence,
            theme_alignments=theme_alignments,
            preference_notes=preference_notes,
            interpreted_eligibility=interpreted_eligibility,
            strengths=strengths,
            gaps=gaps,
            uncertainties=uncertainties,
            rationale=rationale,
        )
        return ValidationOutcome(result, warnings, False)

    def _parse_service_alignments(
        self,
        items: list[Any],
        allowed_ids: set[str],
        opportunity_fields: dict[str, str],
        warnings: list[str],
    ) -> list[ServiceAlignment]:
        parsed: list[ServiceAlignment] = []
        for item in items:
            if not isinstance(item, dict):
                warnings.append("skipped non-object service_alignment")
                continue
            service_id = str(item.get("professional_service_id", ""))
            if service_id not in allowed_ids:
                warnings.append(f"rejected unknown professional_service_id {service_id}")
                continue
            try:
                alignment = AlignmentLevel(str(item.get("alignment", "UNKNOWN")))
                basis = EvidenceBasis(str(item.get("basis", "INFERENCE")))
            except ValueError:
                warnings.append(f"invalid service alignment for {service_id}")
                continue
            refs = self._parse_opportunity_refs(
                item.get("opportunity_refs") or [],
                opportunity_fields,
                warnings,
            )
            parsed.append(
                ServiceAlignment(
                    professional_service_id=service_id,
                    alignment=alignment,
                    basis=basis,
                    rationale=str(item.get("rationale", "")),
                    opportunity_refs=refs,
                )
            )
        return parsed

    def _parse_entity_evidence(
        self,
        items: list[Any],
        allowed_ids: set[str],
        opportunity_fields: dict[str, str],
        warnings: list[str],
        *,
        label: str,
    ) -> list[EntityEvidence]:
        parsed: list[EntityEvidence] = []
        for item in items:
            if not isinstance(item, dict):
                warnings.append(f"skipped non-object {label}_evidence")
                continue
            entity_id = str(item.get("entity_id", ""))
            if entity_id not in allowed_ids:
                warnings.append(f"rejected unknown {label} entity_id {entity_id}")
                continue
            try:
                alignment = AlignmentLevel(str(item.get("alignment", "UNKNOWN")))
                basis = EvidenceBasis(str(item.get("basis", "INFERENCE")))
            except ValueError:
                warnings.append(f"invalid {label} evidence for {entity_id}")
                continue
            refs = self._parse_opportunity_refs(
                item.get("opportunity_refs") or [],
                opportunity_fields,
                warnings,
            )
            parsed.append(
                EntityEvidence(
                    entity_id=entity_id,
                    alignment=alignment,
                    basis=basis,
                    rationale=str(item.get("rationale", "")),
                    opportunity_refs=refs,
                )
            )
        return parsed

    def _parse_theme_alignments(
        self,
        items: list[Any],
        allowed_theme_keys: set[str],
        warnings: list[str],
    ) -> list[ThemeAlignment]:
        parsed: list[ThemeAlignment] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            theme_key = str(item.get("theme_key", ""))
            if theme_key not in allowed_theme_keys:
                warnings.append(f"rejected unknown theme_key {theme_key}")
                continue
            try:
                alignment = AlignmentLevel(str(item.get("alignment", "UNKNOWN")))
                basis = EvidenceBasis(str(item.get("basis", "INFERENCE")))
            except ValueError:
                warnings.append(f"invalid theme alignment for {theme_key}")
                continue
            parsed.append(
                ThemeAlignment(
                    theme_key=theme_key,
                    alignment=alignment,
                    basis=basis,
                    rationale=str(item.get("rationale", "")),
                )
            )
        return parsed

    def _parse_preference_notes(
        self, items: list[Any], warnings: list[str]
    ) -> list[PreferenceNote]:
        parsed: list[PreferenceNote] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                basis = EvidenceBasis(str(item.get("basis", "INFERENCE")))
            except ValueError:
                warnings.append("invalid preference note basis")
                continue
            parsed.append(
                PreferenceNote(
                    criterion_code=str(item.get("criterion_code", "")),
                    basis=basis,
                    note=str(item.get("note", "")),
                )
            )
        return parsed

    def _parse_interpreted_eligibility(
        self, items: list[Any], warnings: list[str]
    ) -> list[InterpretedEligibilityNote]:
        parsed: list[InterpretedEligibilityNote] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                concern = AlignmentLevel(str(item.get("concern_level", "UNKNOWN")))
                basis = EvidenceBasis(str(item.get("basis", "INFERENCE")))
            except ValueError:
                warnings.append("invalid interpreted eligibility item")
                continue
            parsed.append(
                InterpretedEligibilityNote(
                    rule_code=str(item.get("rule_code", "")),
                    concern_level=concern,
                    basis=basis,
                    rationale=str(item.get("rationale", "")),
                )
            )
        return parsed

    def _parse_opportunity_refs(
        self,
        items: list[Any],
        opportunity_fields: dict[str, str],
        warnings: list[str],
    ) -> list[OpportunityEvidenceRef]:
        parsed: list[OpportunityEvidenceRef] = []
        for item in items:
            if not isinstance(item, dict):
                warnings.append("skipped invalid opportunity_ref")
                continue
            try:
                field = OpportunityEvidenceField(str(item.get("field", "")))
            except ValueError:
                warnings.append("invalid opportunity_ref field")
                continue
            excerpt = str(item.get("excerpt", ""))
            source_text = opportunity_fields.get(field.value, "")
            if not excerpt or excerpt not in source_text:
                warnings.append(
                    f"rejected opportunity excerpt not found in {field.value}"
                )
                continue
            parsed.append(OpportunityEvidenceRef(field=field, excerpt=excerpt))
        return parsed
