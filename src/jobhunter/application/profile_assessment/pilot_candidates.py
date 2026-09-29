"""Deterministic pilot opportunity bucketing (read-only selection helpers)."""

from __future__ import annotations

import re
from enum import StrEnum

_PILOT_CATEGORY_ORDER = ("A", "B", "C", "D", "E")


class PilotCategory(StrEnum):
    LAND_LIS = "A"
    GIS_SDI = "B"
    DIGITAL_ADJACENT = "C"
    NON_DOMAIN_ENGINEERING = "D"
    NON_DOMAIN_SPECIALIST = "E"


_CATEGORY_KEYWORDS: dict[PilotCategory, tuple[str, ...]] = {
    PilotCategory.LAND_LIS: (
        "land administration",
        "land information",
        "cadastre",
        "cadastral",
        "land registry",
        "land tenure",
        "lis ",
        " land ",
        "registry",
        "titling",
    ),
    PilotCategory.GIS_SDI: (
        "gis",
        "geospatial",
        "spatial data",
        "postgis",
        "sdi",
        "nsdi",
        "mapping",
        "geo-ict",
    ),
    PilotCategory.DIGITAL_ADJACENT: (
        "digital transformation",
        "interoperability",
        "enterprise architecture",
        "systems integration",
        "e-government",
        "digitization",
        "digitalisation",
    ),
    PilotCategory.NON_DOMAIN_ENGINEERING: (
        "civil engineer",
        "structural engineer",
        "bridge engineer",
        "highway engineer",
        "roads engineer",
        "water engineer",
        "hydraulic",
    ),
    PilotCategory.NON_DOMAIN_SPECIALIST: (
        "hsse",
        "hse officer",
        "health safety",
        "safeguard",
        "gender",
        "social inclusion",
        "gesi",
        "gbv",
        "resettlement specialist",
    ),
}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _phrase_matches(blob: str, phrase: str) -> bool:
    phrase = phrase.strip()
    if not phrase:
        return False
    if " " in phrase:
        return phrase in blob
    return re.search(rf"\b{re.escape(phrase)}\b", blob) is not None


def score_pilot_categories(title: str, description: str | None) -> dict[PilotCategory, int]:
    """Token/phrase overlap scores per pilot bucket (higher = stronger match)."""
    blob = _normalise(f"{title} {(description or '')}")
    scores: dict[PilotCategory, int] = {}
    for category, phrases in _CATEGORY_KEYWORDS.items():
        score = 0
        for phrase in phrases:
            if _phrase_matches(blob, phrase):
                score += 3 if " " in phrase else 1
        scores[category] = score
    return scores


def primary_pilot_category(
    title: str, description: str | None
) -> PilotCategory | None:
    """Best-matching pilot bucket, or None if no signal."""
    scores = score_pilot_categories(title, description)
    best_score = max(scores.values())
    if best_score <= 0:
        return None
    winners = [cat for cat, s in scores.items() if s == best_score]
    if len(winners) == 1:
        return winners[0]
    for code in _PILOT_CATEGORY_ORDER:
        for cat in winners:
            if cat.value == code:
                return cat
    return winners[0]


def pick_one_per_category(
    rows: list[dict],
) -> list[dict]:
    """Choose at most one row per PilotCategory from scored opportunity rows.

    Each row must include ``category`` (PilotCategory) and ``sort_key`` (tuple).
    """
    by_cat: dict[PilotCategory, dict] = {}
    for row in sorted(rows, key=lambda r: r["sort_key"], reverse=True):
        cat = row["category"]
        if cat not in by_cat:
            by_cat[cat] = row
    ordered: list[dict] = []
    for code in _PILOT_CATEGORY_ORDER:
        cat = PilotCategory(code)
        if cat in by_cat:
            ordered.append(by_cat[cat])
    return ordered
