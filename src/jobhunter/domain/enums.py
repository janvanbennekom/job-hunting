"""Domain enumerations for opportunities."""

from __future__ import annotations

from enum import StrEnum


class OpportunityType(StrEnum):
    CONSULTANCY = "CONSULTANCY"
    EMPLOYMENT = "EMPLOYMENT"
    ROSTER = "ROSTER"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class LifecycleStatus(StrEnum):
    NEW = "NEW"
    UPDATED = "UPDATED"
    STILL_OPEN = "STILL_OPEN"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class EligibilityStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
