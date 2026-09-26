"""Enumerations for Phase 7 eligibility evaluation."""

from __future__ import annotations

from enum import StrEnum


class EligibilityRuleKind(StrEnum):
    LIFECYCLE = "LIFECYCLE"
    EXCLUSION = "EXCLUSION"
    HARD_CONSTRAINT = "HARD_CONSTRAINT"


class RuleTriState(StrEnum):
    """Deterministic rule outcome."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
