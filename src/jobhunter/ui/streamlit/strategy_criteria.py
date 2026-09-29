"""Streamlit widgets for structured strategy criterion editing."""

from __future__ import annotations

from typing import Any

import streamlit as st

from jobhunter.domain.strategy_enums import PreferenceStrength


def _strength_select(label: str, current: str, key: str) -> str:
    options = [s.value for s in PreferenceStrength]
    index = options.index(current) if current in options else 0
    return st.selectbox(label, options, index=index, key=key)


def edit_criterion_value(item: dict[str, Any], key_prefix: str) -> dict[str, Any]:
    """Render editors for one criterion; return updated item dict."""
    code = str(item.get("code", ""))
    category = str(item.get("category", ""))
    value = dict(item.get("value") or {})
    strength = item.get("strength")
    updated = {
        "category": category,
        "code": code,
        "value": value,
        "strength": strength,
    }

    st.markdown(f"**{code.replace('_', ' ').title()}** ({category})")
    if code == "ASSIGNMENT_DELIVERY_MODE":
        value = {
            "implementation": _strength_select(
                "Implementation",
                str(value.get("implementation", PreferenceStrength.PREFERRED.value)),
                f"{key_prefix}-impl",
            ),
            "advisory": _strength_select(
                "Advisory",
                str(value.get("advisory", PreferenceStrength.PREFERRED.value)),
                f"{key_prefix}-adv",
            ),
        }
    elif code == "WORK_MODE":
        value = {
            "remote": _strength_select(
                "Remote",
                str(value.get("remote", PreferenceStrength.ACCEPTABLE.value)),
                f"{key_prefix}-remote",
            ),
            "hybrid": _strength_select(
                "Hybrid",
                str(value.get("hybrid", PreferenceStrength.ACCEPTABLE.value)),
                f"{key_prefix}-hybrid",
            ),
            "on_site": _strength_select(
                "On site",
                str(value.get("on_site", PreferenceStrength.ACCEPTABLE.value)),
                f"{key_prefix}-onsite",
            ),
        }
    elif code == "TRAVEL_PATTERN":
        value = {"aspect": "continuous_abroad"}
        st.caption("Travel pattern aspect: continuous abroad")
    elif code == "ASSIGNMENT_DURATION":
        if category == "HARD_CONSTRAINT":
            min_m = st.number_input(
                "Min months",
                min_value=0,
                value=int(value.get("min_months") or 0),
                key=f"{key_prefix}-min",
            )
            max_m = st.number_input(
                "Max months",
                min_value=0,
                value=int(value.get("max_months") or 0),
                key=f"{key_prefix}-max",
            )
            value = {
                "min_months": min_m or None,
                "max_months": max_m or None,
            }
        else:
            value = {
                "ideal_min_months": st.number_input(
                    "Ideal min months",
                    min_value=0,
                    value=int(value.get("ideal_min_months") or 0),
                    key=f"{key_prefix}-imin",
                )
                or None,
                "ideal_max_months": st.number_input(
                    "Ideal max months",
                    min_value=0,
                    value=int(value.get("ideal_max_months") or 0),
                    key=f"{key_prefix}-imax",
                )
                or None,
            }
    elif code == "ENGAGEMENT_MODEL":
        if category == "HARD_CONSTRAINT":
            value = {
                "single_consultant_only": st.checkbox(
                    "Single consultant only",
                    value=bool(value.get("single_consultant_only")),
                    key=f"{key_prefix}-sco",
                )
            }
        else:
            value = {
                "international_consultancy": _strength_select(
                    "International consultancy",
                    str(
                        value.get(
                            "international_consultancy",
                            PreferenceStrength.PREFERRED.value,
                        )
                    ),
                    f"{key_prefix}-intl",
                ),
                "single_consultant_engagement": _strength_select(
                    "Single consultant engagement",
                    str(
                        value.get(
                            "single_consultant_engagement",
                            PreferenceStrength.PREFERRED.value,
                        )
                    ),
                    f"{key_prefix}-single",
                ),
            }
    elif code == "GEOGRAPHY":
        if category == "HARD_CONSTRAINT":
            raw = st.text_input(
                "Excluded countries (comma-separated)",
                value=", ".join(value.get("excluded_countries") or []),
                key=f"{key_prefix}-excl",
            )
            countries = [part.strip() for part in raw.split(",") if part.strip()]
            value = {"excluded_countries": countries}
        else:
            st.caption("Edit regions/countries as name|STRENGTH per line.")
            region_lines = st.text_area(
                "Regions",
                value=_places_to_lines(value.get("regions") or []),
                key=f"{key_prefix}-regions",
            )
            country_lines = st.text_area(
                "Countries",
                value=_places_to_lines(value.get("countries") or []),
                key=f"{key_prefix}-countries",
            )
            value = {
                "regions": _lines_to_places(region_lines),
                "countries": _lines_to_places(country_lines),
            }
    else:
        st.caption("No structured editor for this parameter; value unchanged.")

    updated["value"] = value
    return updated


def _places_to_lines(places: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{p.get('name', '')}|{p.get('strength', '')}" for p in places if p.get("name")
    )


def _lines_to_places(text: str) -> list[dict[str, str]]:
    places: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            name, strength = line.split("|", 1)
            places.append({"name": name.strip(), "strength": strength.strip()})
        else:
            places.append(
                {
                    "name": line,
                    "strength": PreferenceStrength.ACCEPTABLE.value,
                }
            )
    return places
