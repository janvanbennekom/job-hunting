"""Deterministic assessment model for tests."""

from __future__ import annotations

import json
from typing import Any

from jobhunter.ai.protocol import AssessmentModelResponse
from jobhunter.domain.assessment_enums import (
    AlignmentLevel,
    EvidenceBasis,
    OverallRelevance,
    SourceDataSufficiency,
)
from jobhunter.domain.assessment_request import AssessmentRequest


class FakeAssessmentModel:
    """Returns scripted JSON based on opportunity content and configured mode."""

    provider = "fake"
    model_name = "fake-assessment-v1"

    def __init__(
        self,
        *,
        mode: str = "auto",
        fixed_payload: dict[str, Any] | None = None,
        raise_provider_error: bool = False,
        malformed: bool = False,
    ) -> None:
        self.mode = mode
        self.fixed_payload = fixed_payload
        self.raise_provider_error = raise_provider_error
        self.malformed = malformed
        self.call_count = 0

    def assess(self, request: AssessmentRequest) -> AssessmentModelResponse:
        self.call_count += 1
        if self.raise_provider_error:
            return AssessmentModelResponse(
                provider=self.provider,
                model_name=self.model_name,
                error="simulated provider failure",
            )
        if self.malformed:
            return AssessmentModelResponse(
                provider=self.provider,
                model_name=self.model_name,
                raw_text="{not-json",
            )

        if self.fixed_payload is not None:
            payload = dict(self.fixed_payload)
        else:
            payload = self._auto_payload(request)

        return AssessmentModelResponse(
            provider=self.provider,
            model_name=self.model_name,
            parsed=payload,
            raw_text=json.dumps(payload),
        )

    def _auto_payload(self, request: AssessmentRequest) -> dict[str, Any]:
        opportunity = request.opportunity
        title = str(opportunity.get("title", "")).lower()
        sufficiency = request.source_data_sufficiency.value

        if self.mode == "weak":
            return self._base_payload(
                OverallRelevance.OUT_OF_SCOPE.value,
                sufficiency,
                [],
                [],
            )

        if "unrelated" in title or "marketing" in title:
            return self._base_payload(
                OverallRelevance.OUT_OF_SCOPE.value,
                sufficiency,
                [],
                [],
            )

        services = request.evidence_pack.professional_services
        assignments = request.evidence_pack.assignments
        service_id = services[0].id if services else ""
        assignment_id = assignments[0].id if assignments else ""

        if "lis" in title or "land information" in title:
            excerpt = request.opportunity_prompt_text.get("TITLE", "") or title
            return self._base_payload(
                OverallRelevance.STRONG_FIT.value,
                sufficiency,
                [
                    {
                        "professional_service_id": service_id,
                        "alignment": AlignmentLevel.STRONG.value,
                        "basis": EvidenceBasis.INFERENCE.value,
                        "rationale": "Title aligns with LIS implementation scope.",
                        "opportunity_refs": [
                            {"field": "TITLE", "excerpt": excerpt},
                        ],
                    }
                ],
                [
                    {
                        "entity_id": assignment_id,
                        "alignment": AlignmentLevel.MODERATE.value,
                        "basis": EvidenceBasis.PROFILE_FACT.value,
                        "rationale": "Selected assignment evidence supplied in context.",
                        "opportunity_refs": [],
                    }
                ]
                if assignment_id
                else [],
            )

        return self._base_payload(
            OverallRelevance.WEAK_FIT.value,
            sufficiency,
            [],
            [],
            uncertainties=["Limited opportunity detail supplied."],
        )

    def _base_payload(
        self,
        overall: str,
        sufficiency: str,
        service_alignments: list[dict[str, Any]],
        assignment_evidence: list[dict[str, Any]],
        *,
        uncertainties: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "overall_relevance": overall,
            "source_data_sufficiency": sufficiency,
            "professional_relevance": {
                "scope_summary": "Automated fake assessment.",
                "delivery_mode_inference": "UNKNOWN",
                "seniority_inference": "UNKNOWN",
                "domain_tags": [],
            },
            "service_alignments": service_alignments,
            "assignment_evidence": assignment_evidence,
            "capability_evidence": [],
            "skill_evidence": [],
            "language_evidence": [],
            "country_evidence": [],
            "theme_alignments": [],
            "preference_notes": [],
            "interpreted_eligibility": [],
            "strengths": [],
            "gaps": [],
            "uncertainties": uncertainties or [],
            "rationale": "FakeAssessmentModel response.",
        }
