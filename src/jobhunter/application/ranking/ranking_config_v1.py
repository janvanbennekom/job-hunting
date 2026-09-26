"""Versioned deterministic ranking weights and thresholds (ranking_v1).

Internal integer points are used only for ordering and audit. They are not
match percentages or probabilities. User-facing output is priority bands plus
factors.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from jobhunter.domain.assessment_enums import (
    AlignmentLevel,
    OverallRelevance,
    SourceDataSufficiency,
)
from jobhunter.domain.enums import EligibilityStatus
from jobhunter.domain.strategy_enums import PreferenceStrength

# --- Overall relevance (primary fit signal) ---
OVERALL_RELEVANCE_POINTS: dict[OverallRelevance, int] = {
    OverallRelevance.STRONG_FIT: 400,
    OverallRelevance.MODERATE_FIT: 300,
    OverallRelevance.WEAK_FIT: 200,
    OverallRelevance.OUT_OF_SCOPE: 100,
    OverallRelevance.INSUFFICIENT_EVIDENCE: 50,
    OverallRelevance.UNKNOWN: 50,
}

# --- Service alignment (best single service) ---
SERVICE_ALIGNMENT_POINTS: dict[AlignmentLevel, int] = {
    AlignmentLevel.STRONG: 60,
    AlignmentLevel.MODERATE: 40,
    AlignmentLevel.WEAK: 20,
    AlignmentLevel.NONE: 0,
    AlignmentLevel.UNKNOWN: 0,
    AlignmentLevel.INSUFFICIENT_EVIDENCE: 0,
}

# --- Theme alignment × theme preference strength ---
THEME_ALIGNMENT_POINTS: dict[AlignmentLevel, int] = {
    AlignmentLevel.STRONG: 30,
    AlignmentLevel.MODERATE: 20,
    AlignmentLevel.WEAK: 10,
    AlignmentLevel.NONE: 0,
    AlignmentLevel.UNKNOWN: 0,
    AlignmentLevel.INSUFFICIENT_EVIDENCE: 0,
}

THEME_STRENGTH_MULTIPLIER: dict[PreferenceStrength, int] = {
    PreferenceStrength.STRONGLY_PREFERRED: 4,
    PreferenceStrength.PREFERRED: 3,
    PreferenceStrength.ACCEPTABLE: 2,
    PreferenceStrength.LESS_PREFERRED: 1,
}

THEME_CONTRIBUTION_CAP = 120

# --- Eligibility uncertainty (not gating) ---
ELIGIBILITY_STATUS_POINTS: dict[EligibilityStatus, int] = {
    EligibilityStatus.ELIGIBLE: 0,
    EligibilityStatus.REVIEW_REQUIRED: -40,
    EligibilityStatus.UNKNOWN: -30,
    EligibilityStatus.INELIGIBLE: 0,
}

# --- Source data sufficiency (evidence quality, not relevance ceiling) ---
SOURCE_SUFFICIENCY_POINTS: dict[SourceDataSufficiency, int] = {
    SourceDataSufficiency.LIST_SUMMARY_ONLY: -25,
    SourceDataSufficiency.PARTIAL: -10,
    SourceDataSufficiency.ADEQUATE: 0,
}

# --- Interpreted eligibility concerns (structured concern_level) ---
INTERPRETED_CONCERN_POINTS: dict[AlignmentLevel, int] = {
    AlignmentLevel.STRONG: -20,
    AlignmentLevel.MODERATE: -10,
    AlignmentLevel.WEAK: -5,
    AlignmentLevel.NONE: 0,
    AlignmentLevel.UNKNOWN: 0,
    AlignmentLevel.INSUFFICIENT_EVIDENCE: 0,
}
INTERPRETED_CONCERN_CAP = -30

# --- Priority band thresholds (after internal score computed) ---
# STRONG_FIT (400) + LIST_SUMMARY_ONLY (-25) = 375 must remain able to reach HIGH.
BAND_HIGH_MIN_SCORE = 370
BAND_MEDIUM_MIN_SCORE = 250

# Eligibility statuses that force REVIEW band when rankable
ELIGIBILITY_REVIEW_BAND = frozenset(
    {EligibilityStatus.REVIEW_REQUIRED, EligibilityStatus.UNKNOWN}
)


def config_payload() -> dict[str, Any]:
    """Canonical configuration document for hashing."""
    return {
        "version": "ranking_config_v1",
        "overall_relevance_points": {
            k.value: v for k, v in OVERALL_RELEVANCE_POINTS.items()
        },
        "service_alignment_points": {
            k.value: v for k, v in SERVICE_ALIGNMENT_POINTS.items()
        },
        "theme_alignment_points": {
            k.value: v for k, v in THEME_ALIGNMENT_POINTS.items()
        },
        "theme_strength_multiplier": {
            k.value: v for k, v in THEME_STRENGTH_MULTIPLIER.items()
        },
        "theme_contribution_cap": THEME_CONTRIBUTION_CAP,
        "eligibility_status_points": {
            k.value: v for k, v in ELIGIBILITY_STATUS_POINTS.items()
        },
        "source_sufficiency_points": {
            k.value: v for k, v in SOURCE_SUFFICIENCY_POINTS.items()
        },
        "interpreted_concern_points": {
            k.value: v for k, v in INTERPRETED_CONCERN_POINTS.items()
        },
        "interpreted_concern_cap": INTERPRETED_CONCERN_CAP,
        "band_high_min_score": BAND_HIGH_MIN_SCORE,
        "band_medium_min_score": BAND_MEDIUM_MIN_SCORE,
    }


def compute_ranking_config_hash() -> str:
    canonical = json.dumps(config_payload(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
