"""Pilot opportunity bucketing (deterministic, no DB)."""

from __future__ import annotations

from jobhunter.application.profile_assessment.pilot_candidates import (
    PilotCategory,
    primary_pilot_category,
    score_pilot_categories,
)


def test_land_category() -> None:
    cat = primary_pilot_category(
        "National land administration and cadastre specialist",
        "Land registry implementation.",
    )
    assert cat is PilotCategory.LAND_LIS


def test_gis_category() -> None:
    cat = primary_pilot_category(
        "GIS database developer for spatial data infrastructure",
        "PostGIS and SDI.",
    )
    assert cat is PilotCategory.GIS_SDI


def test_civil_engineer_category() -> None:
    cat = primary_pilot_category("Civil Engineer", "Structural design.")
    assert cat is PilotCategory.NON_DOMAIN_ENGINEERING


def test_gis_not_matched_inside_strategic() -> None:
    scores = score_pilot_categories(
        "Strategic communications advisor",
        "Stakeholder engagement.",
    )
    assert scores[PilotCategory.GIS_SDI] == 0


def test_hsse_category() -> None:
    cat = primary_pilot_category(
        "Health, Safety, Social and Environmental Officer",
        "Safeguard compliance.",
    )
    assert cat is PilotCategory.NON_DOMAIN_SPECIALIST
