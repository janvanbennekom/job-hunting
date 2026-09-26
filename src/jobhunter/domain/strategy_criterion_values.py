"""Structured StrategyCriterion values (validated per StrategyParameterCode)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jobhunter.domain.strategy_enums import (
    PreferenceStrength,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.domain.identifiers import require_non_empty
from jobhunter.domain.strategy_validation import (
    reject_unknown_keys,
    require_non_empty_string_list,
    require_positive_int,
    require_strength,
)


@dataclass(frozen=True, slots=True)
class AssignmentDeliveryModeValue:
    implementation: PreferenceStrength
    advisory: PreferenceStrength


@dataclass(frozen=True, slots=True)
class WorkModePreferenceValue:
    remote: PreferenceStrength
    hybrid: PreferenceStrength
    on_site: PreferenceStrength


@dataclass(frozen=True, slots=True)
class TravelPatternPreferenceValue:
    aspect: str

    def __post_init__(self) -> None:
        if self.aspect != "continuous_abroad":
            raise ValueError(
                "TravelPatternPreferenceValue.aspect must be 'continuous_abroad'"
            )


@dataclass(frozen=True, slots=True)
class GeographyPlacePreference:
    """One region or country with its own ordinal preference."""

    name: str
    strength: PreferenceStrength

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", require_non_empty(self.name, "name"))


@dataclass(frozen=True, slots=True)
class GeographyPreferenceValue:
    regions: tuple[GeographyPlacePreference, ...] = ()
    countries: tuple[GeographyPlacePreference, ...] = ()


@dataclass(frozen=True, slots=True)
class GeographyConstraintValue:
    excluded_countries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AssignmentDurationPreferenceValue:
    ideal_min_months: int | None = None
    ideal_max_months: int | None = None

    def __post_init__(self) -> None:
        if self.ideal_min_months is not None:
            require_positive_int(self.ideal_min_months, "ideal_min_months")
        if self.ideal_max_months is not None:
            require_positive_int(self.ideal_max_months, "ideal_max_months")
        if (
            self.ideal_min_months is not None
            and self.ideal_max_months is not None
            and self.ideal_min_months > self.ideal_max_months
        ):
            raise ValueError("ideal_min_months cannot exceed ideal_max_months")


@dataclass(frozen=True, slots=True)
class AssignmentDurationConstraintValue:
    min_months: int | None = None
    max_months: int | None = None

    def __post_init__(self) -> None:
        if self.min_months is None and self.max_months is None:
            raise ValueError(
                "AssignmentDurationConstraintValue requires min_months or max_months"
            )
        if self.min_months is not None:
            require_positive_int(self.min_months, "min_months")
        if self.max_months is not None:
            require_positive_int(self.max_months, "max_months")
        if (
            self.min_months is not None
            and self.max_months is not None
            and self.min_months > self.max_months
        ):
            raise ValueError("min_months cannot exceed max_months")


@dataclass(frozen=True, slots=True)
class EngagementModelPreferenceValue:
    international_consultancy: PreferenceStrength
    single_consultant_engagement: PreferenceStrength


@dataclass(frozen=True, slots=True)
class EngagementModelConstraintValue:
    single_consultant_only: bool


def _parse_geography_place_list(
    raw: Any,
    field_name: str,
) -> tuple[GeographyPlacePreference, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"{field_name} must be a list")
    places: list[GeographyPlacePreference] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{field_name}[{index}] must be a mapping")
        reject_unknown_keys(
            item,
            frozenset({"name", "strength"}),
            f"{field_name}[{index}]",
        )
        places.append(
            GeographyPlacePreference(
                name=str(item["name"]),
                strength=require_strength(item["strength"], f"{field_name}.strength"),
            )
        )
    return tuple(places)


CriterionValue = (
    AssignmentDeliveryModeValue
    | WorkModePreferenceValue
    | TravelPatternPreferenceValue
    | GeographyPreferenceValue
    | GeographyConstraintValue
    | AssignmentDurationPreferenceValue
    | AssignmentDurationConstraintValue
    | EngagementModelPreferenceValue
    | EngagementModelConstraintValue
)


def parse_criterion_value(
    category: StrategyCriterionCategory,
    code: StrategyParameterCode,
    raw: dict[str, Any],
) -> CriterionValue:
    if code is StrategyParameterCode.ASSIGNMENT_DELIVERY_MODE:
        if category is not StrategyCriterionCategory.PREFERENCE:
            raise ValueError(
                "ASSIGNMENT_DELIVERY_MODE is only valid for PREFERENCE"
            )
        return AssignmentDeliveryModeValue(
            implementation=require_strength(raw["implementation"], "implementation"),
            advisory=require_strength(raw["advisory"], "advisory"),
        )
    if code is StrategyParameterCode.WORK_MODE:
        if category is not StrategyCriterionCategory.PREFERENCE:
            raise ValueError("WORK_MODE is only valid for PREFERENCE")
        for field in ("remote", "hybrid", "on_site"):
            if field not in raw:
                raise ValueError(f"WORK_MODE requires {field}")
        return WorkModePreferenceValue(
            remote=require_strength(raw["remote"], "remote"),
            hybrid=require_strength(raw["hybrid"], "hybrid"),
            on_site=require_strength(raw["on_site"], "on_site"),
        )
    if code is StrategyParameterCode.TRAVEL_PATTERN:
        if category is not StrategyCriterionCategory.PREFERENCE:
            raise ValueError("TRAVEL_PATTERN is only valid for PREFERENCE")
        aspect = raw.get("aspect")
        if not isinstance(aspect, str):
            raise ValueError("TRAVEL_PATTERN requires string aspect")
        return TravelPatternPreferenceValue(aspect=aspect.strip())
    if code is StrategyParameterCode.GEOGRAPHY:
        if category is StrategyCriterionCategory.PREFERENCE:
            reject_unknown_keys(
                raw,
                frozenset({"regions", "countries"}),
                "GEOGRAPHY preference value",
            )
            return GeographyPreferenceValue(
                regions=_parse_geography_place_list(raw.get("regions"), "regions"),
                countries=_parse_geography_place_list(
                    raw.get("countries"), "countries"
                ),
            )
        reject_unknown_keys(
            raw,
            frozenset({"excluded_countries"}),
            "GEOGRAPHY constraint value",
        )
        return GeographyConstraintValue(
            excluded_countries=require_non_empty_string_list(
                raw["excluded_countries"], "excluded_countries", allow_empty=False
            ),
        )
    if code is StrategyParameterCode.ASSIGNMENT_DURATION:
        if category is StrategyCriterionCategory.PREFERENCE:
            return AssignmentDurationPreferenceValue(
                ideal_min_months=raw.get("ideal_min_months"),
                ideal_max_months=raw.get("ideal_max_months"),
            )
        return AssignmentDurationConstraintValue(
            min_months=raw.get("min_months"),
            max_months=raw.get("max_months"),
        )
    if code is StrategyParameterCode.ENGAGEMENT_MODEL:
        if category is StrategyCriterionCategory.PREFERENCE:
            return EngagementModelPreferenceValue(
                international_consultancy=require_strength(
                    raw["international_consultancy"], "international_consultancy"
                ),
                single_consultant_engagement=require_strength(
                    raw["single_consultant_engagement"],
                    "single_consultant_engagement",
                ),
            )
        return EngagementModelConstraintValue(
            single_consultant_only=bool(raw["single_consultant_only"]),
        )
    raise ValueError(f"Unsupported StrategyParameterCode: {code}")


def criterion_value_to_mapping(value: CriterionValue) -> dict[str, Any]:
    if isinstance(value, AssignmentDeliveryModeValue):
        return {
            "implementation": value.implementation.value,
            "advisory": value.advisory.value,
        }
    if isinstance(value, WorkModePreferenceValue):
        return {
            "remote": value.remote.value,
            "hybrid": value.hybrid.value,
            "on_site": value.on_site.value,
        }
    if isinstance(value, TravelPatternPreferenceValue):
        return {"aspect": value.aspect}
    if isinstance(value, GeographyPreferenceValue):
        return {
            "regions": [
                {"name": place.name, "strength": place.strength.value}
                for place in value.regions
            ],
            "countries": [
                {"name": place.name, "strength": place.strength.value}
                for place in value.countries
            ],
        }
    if isinstance(value, GeographyConstraintValue):
        return {"excluded_countries": list(value.excluded_countries)}
    if isinstance(value, AssignmentDurationPreferenceValue):
        return {
            "ideal_min_months": value.ideal_min_months,
            "ideal_max_months": value.ideal_max_months,
        }
    if isinstance(value, AssignmentDurationConstraintValue):
        return {"min_months": value.min_months, "max_months": value.max_months}
    if isinstance(value, EngagementModelPreferenceValue):
        return {
            "international_consultancy": value.international_consultancy.value,
            "single_consultant_engagement": value.single_consultant_engagement.value,
        }
    if isinstance(value, EngagementModelConstraintValue):
        return {"single_consultant_only": value.single_consultant_only}
    raise TypeError(f"Unknown criterion value type: {type(value)!r}")
