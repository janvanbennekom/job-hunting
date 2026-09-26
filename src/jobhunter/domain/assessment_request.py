"""Structured assessment request passed to AssessmentModel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.assessment_enums import SourceDataSufficiency
from jobhunter.domain.evidence_context_pack import EvidenceContextPack


@dataclass(slots=True)
class AssessmentRequest:
    schema_version: str
    opportunity: dict[str, Any]
    opportunity_prompt_text: dict[str, str]
    source_data_sufficiency: SourceDataSufficiency
    evidence_pack: EvidenceContextPack
    search_themes: list[dict[str, Any]]
    preference_criteria: list[dict[str, Any]]
    eligibility_rule_summaries: list[dict[str, Any]]
    instructions: str = field(default="")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "opportunity": self.opportunity,
            "opportunity_prompt_text": self.opportunity_prompt_text,
            "source_data_sufficiency": self.source_data_sufficiency.value,
            "evidence_pack": self.evidence_pack.to_mapping(),
            "search_themes": self.search_themes,
            "preference_criteria": self.preference_criteria,
            "eligibility_rule_summaries": self.eligibility_rule_summaries,
            "instructions": self.instructions,
        }
