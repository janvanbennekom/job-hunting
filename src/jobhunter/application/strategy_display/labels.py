"""Human-readable labels for search strategy enums (UI only)."""

from __future__ import annotations

from jobhunter.domain.strategy_enums import (
    ExclusionCode,
    PreferenceStrength,
    StrategyCriterionCategory,
    StrategyParameterCode,
)

_STRENGTH_LABELS = {
    PreferenceStrength.STRONGLY_PREFERRED: "Strong",
    PreferenceStrength.PREFERRED: "Preferred",
    PreferenceStrength.ACCEPTABLE: "Acceptable",
    PreferenceStrength.LESS_PREFERRED: "Less preferred",
}

_CATEGORY_LABELS = {
    StrategyCriterionCategory.PREFERENCE: "Preference",
    StrategyCriterionCategory.HARD_CONSTRAINT: "Hard constraint",
}

_PARAMETER_LABELS = {
    StrategyParameterCode.ASSIGNMENT_DELIVERY_MODE: "Assignment delivery mode",
    StrategyParameterCode.GEOGRAPHY: "Geography",
    StrategyParameterCode.ASSIGNMENT_DURATION: "Assignment duration",
    StrategyParameterCode.TRAVEL_PATTERN: "Travel pattern",
    StrategyParameterCode.WORK_MODE: "Work mode",
    StrategyParameterCode.ENGAGEMENT_MODEL: "Engagement model",
}

_EXCLUSION_LABELS = {
    ExclusionCode.REQUIRES_MULTI_PERSON_TEAM_OR_CONSORTIUM: (
        "Requires multi-person team or consortium"
    ),
    ExclusionCode.NATIONAL_CONSULTANT_ONLY: "National consultant only",
    ExclusionCode.JUNIOR_OR_INTERNSHIP: "Junior or internship",
    ExclusionCode.VOLUNTEER: "Volunteer",
}

_CHANGE_SOURCE_LABELS = {
    "INITIAL_SEED": "Initial seed",
    "MANUAL": "Manual",
    "STRUCTURED_EDIT": "Structured edit",
    "CONVERSATION_CONFIRMED": "Conversational change",
    "IMPORT": "Import",
}


def label_strength(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _STRENGTH_LABELS.get(PreferenceStrength(value), value)
    except ValueError:
        return value


def label_category(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _CATEGORY_LABELS.get(StrategyCriterionCategory(value), value)
    except ValueError:
        return value


def label_parameter_code(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _PARAMETER_LABELS.get(StrategyParameterCode(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_exclusion_code(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return _EXCLUSION_LABELS.get(ExclusionCode(value), value)
    except ValueError:
        return value.replace("_", " ").title()


def label_change_source(value: str | None) -> str:
    if not value:
        return "—"
    return _CHANGE_SOURCE_LABELS.get(value, value.replace("_", " ").title())
