"""Validated structured assessment result (Phase 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.assessment_enums import (
    AlignmentLevel,
    EvidenceBasis,
    OpportunityEvidenceField,
    OverallRelevance,
    SourceDataSufficiency,
)


@dataclass(slots=True)
class OpportunityEvidenceRef:
    field: OpportunityEvidenceField
    excerpt: str


@dataclass(slots=True)
class ServiceAlignment:
    professional_service_id: str
    alignment: AlignmentLevel
    basis: EvidenceBasis
    rationale: str
    opportunity_refs: list[OpportunityEvidenceRef] = field(default_factory=list)


@dataclass(slots=True)
class EntityEvidence:
    entity_id: str
    alignment: AlignmentLevel
    basis: EvidenceBasis
    rationale: str
    opportunity_refs: list[OpportunityEvidenceRef] = field(default_factory=list)


@dataclass(slots=True)
class ThemeAlignment:
    theme_key: str
    alignment: AlignmentLevel
    basis: EvidenceBasis
    rationale: str


@dataclass(slots=True)
class InterpretedEligibilityNote:
    rule_code: str
    concern_level: AlignmentLevel
    basis: EvidenceBasis
    rationale: str


@dataclass(slots=True)
class PreferenceNote:
    criterion_code: str
    basis: EvidenceBasis
    note: str


@dataclass(slots=True)
class ProfessionalRelevanceSection:
    scope_summary: str
    delivery_mode_inference: str
    seniority_inference: str
    domain_tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AssessmentResult:
    overall_relevance: OverallRelevance
    source_data_sufficiency: SourceDataSufficiency
    professional_relevance: ProfessionalRelevanceSection
    service_alignments: list[ServiceAlignment] = field(default_factory=list)
    assignment_evidence: list[EntityEvidence] = field(default_factory=list)
    capability_evidence: list[EntityEvidence] = field(default_factory=list)
    skill_evidence: list[EntityEvidence] = field(default_factory=list)
    language_evidence: list[EntityEvidence] = field(default_factory=list)
    country_evidence: list[EntityEvidence] = field(default_factory=list)
    theme_alignments: list[ThemeAlignment] = field(default_factory=list)
    preference_notes: list[PreferenceNote] = field(default_factory=list)
    interpreted_eligibility: list[InterpretedEligibilityNote] = field(
        default_factory=list
    )
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_mapping(self) -> dict[str, Any]:
        return {
            "overall_relevance": self.overall_relevance.value,
            "source_data_sufficiency": self.source_data_sufficiency.value,
            "professional_relevance": {
                "scope_summary": self.professional_relevance.scope_summary,
                "delivery_mode_inference": (
                    self.professional_relevance.delivery_mode_inference
                ),
                "seniority_inference": (
                    self.professional_relevance.seniority_inference
                ),
                "domain_tags": list(self.professional_relevance.domain_tags),
            },
            "service_alignments": [
                {
                    "professional_service_id": s.professional_service_id,
                    "alignment": s.alignment.value,
                    "basis": s.basis.value,
                    "rationale": s.rationale,
                    "opportunity_refs": [
                        {"field": r.field.value, "excerpt": r.excerpt}
                        for r in s.opportunity_refs
                    ],
                }
                for s in self.service_alignments
            ],
            "assignment_evidence": [_entity_evidence_mapping(e) for e in self.assignment_evidence],
            "capability_evidence": [_entity_evidence_mapping(e) for e in self.capability_evidence],
            "skill_evidence": [_entity_evidence_mapping(e) for e in self.skill_evidence],
            "language_evidence": [_entity_evidence_mapping(e) for e in self.language_evidence],
            "country_evidence": [_entity_evidence_mapping(e) for e in self.country_evidence],
            "theme_alignments": [
                {
                    "theme_key": t.theme_key,
                    "alignment": t.alignment.value,
                    "basis": t.basis.value,
                    "rationale": t.rationale,
                }
                for t in self.theme_alignments
            ],
            "preference_notes": [
                {
                    "criterion_code": p.criterion_code,
                    "basis": p.basis.value,
                    "note": p.note,
                }
                for p in self.preference_notes
            ],
            "interpreted_eligibility": [
                {
                    "rule_code": i.rule_code,
                    "concern_level": i.concern_level.value,
                    "basis": i.basis.value,
                    "rationale": i.rationale,
                }
                for i in self.interpreted_eligibility
            ],
            "strengths": list(self.strengths),
            "gaps": list(self.gaps),
            "uncertainties": list(self.uncertainties),
            "rationale": self.rationale,
        }


def _entity_evidence_mapping(entity: EntityEvidence) -> dict[str, Any]:
    return {
        "entity_id": entity.entity_id,
        "alignment": entity.alignment.value,
        "basis": entity.basis.value,
        "rationale": entity.rationale,
        "opportunity_refs": [
            {"field": r.field.value, "excerpt": r.excerpt}
            for r in entity.opportunity_refs
        ],
    }
