"""Assessment model output contract (included in OpenAI prompts)."""

from __future__ import annotations

from jobhunter.domain.assessment_enums import OverallRelevance

OVERALL_RELEVANCE_VALUES = [member.value for member in OverallRelevance]


def assessment_output_instructions() -> str:
    """Semantic guidance for overall_relevance and required narrative fields."""
    return (
        "You must return a single JSON object matching the output schema below.\n"
        "overall_relevance is required and must be one of: "
        + ", ".join(OVERALL_RELEVANCE_VALUES)
        + ".\n"
        "Semantic rules for overall_relevance:\n"
        "- STRONG_FIT: the opportunity's substantive professional work is clearly within "
        "the candidate's Geo-ICT / land administration / LIS / GIS / SDI / spatial "
        "data / interoperability / systems-integration / digital-transformation-for-"
        "land-agencies scope, with strong direct supporting profile evidence for that "
        "same professional focus (not merely transferable generic IT skills).\n"
        "- MODERATE_FIT: professionally adjacent or partially in scope (e.g. broad "
        "digitalisation, enterprise IT, programme management) where profile evidence "
        "supports credible delivery but the posting does not centre land/geospatial "
        "professional work, or material gaps/uncertainty remain.\n"
        "- WEAK_FIT: professionally related enough to consider, but limited evidence "
        "or substantial gaps.\n"
        "- OUT_OF_SCOPE: the substantive professional discipline is outside the target "
        "profile (e.g. civil engineering, HSSE/safeguards-only, gender/social "
        "inclusion specialist, audit/evaluation-only, HR/finance) even if generic "
        "international or public-sector experience overlaps.\n"
        "- INSUFFICIENT_EVIDENCE: source text is too sparse to judge professional fit.\n"
        "- UNKNOWN: only when source information is genuinely insufficient to determine "
        "professional relevance — not because the role is a poor match.\n"
        "When source_data_sufficiency is ADEQUATE or PARTIAL and the title/description "
        "describe the role, you must set professional_relevance.scope_summary and "
        "rationale with substantive text and choose OUT_OF_SCOPE, WEAK_FIT, or a stronger "
        "fit — not UNKNOWN with empty fields.\n"
        "Ground service_alignments and entity evidence using only IDs from evidence_pack.\n"
        "assignment_evidence, capability_evidence, skill_evidence, language_evidence, "
        "and country_evidence must each be a JSON array of objects (never strings). "
        "Each object needs entity_id, alignment, basis, rationale, and optional "
        "opportunity_refs.\n"
        "opportunity_refs excerpts must be exact substrings of the supplied opportunity "
        "field text (no paraphrase)."
    )


def assessment_output_schema() -> dict:
    """JSON-schema-like description embedded in the model prompt (not OpenAI strict mode)."""
    return {
        "overall_relevance": f"enum: {OVERALL_RELEVANCE_VALUES}",
        "source_data_sufficiency": "enum: LIST_SUMMARY_ONLY | PARTIAL | ADEQUATE",
        "professional_relevance": {
            "scope_summary": "string (required, non-empty when sufficiency is not LIST_SUMMARY_ONLY)",
            "delivery_mode_inference": "string",
            "seniority_inference": "string",
            "domain_tags": ["string"],
        },
        "service_alignments": [
            {
                "professional_service_id": "string (from evidence_pack)",
                "alignment": "STRONG|MODERATE|WEAK|NONE|UNKNOWN|INSUFFICIENT_EVIDENCE",
                "basis": "OPPORTUNITY_FACT|PROFILE_FACT|INFERENCE",
                "rationale": "string",
                "opportunity_refs": [{"field": "TITLE|DESCRIPTION|...", "excerpt": "substring"}],
            }
        ],
        "assignment_evidence": ["..."],
        "capability_evidence": ["..."],
        "skill_evidence": ["..."],
        "language_evidence": ["..."],
        "country_evidence": ["..."],
        "theme_alignments": ["..."],
        "preference_notes": ["..."],
        "interpreted_eligibility": ["..."],
        "strengths": ["string"],
        "gaps": ["string"],
        "uncertainties": ["string"],
        "rationale": "string (required summary, non-empty when sufficiency is not LIST_SUMMARY_ONLY)",
    }
