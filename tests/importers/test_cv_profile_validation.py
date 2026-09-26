"""Unit tests for CV profile seed validation."""

from __future__ import annotations

from jobhunter.infrastructure.importers.cv_profile.types import (
    CountrySeedRow,
    CvProfileSeed,
    LanguageSeedRow,
    SkillSeedRow,
)
from jobhunter.infrastructure.importers.cv_profile.validation import validate_seed


def _minimal_seed(**overrides) -> CvProfileSeed:
    countries = [
        CountrySeedRow(country=f"C{i}", notes=None) for i in range(31)
    ]
    base = CvProfileSeed(
        schema_version=1,
        source_reference="tests/minimal.json",
        document_title="CV",
        document_version_label=None,
        profile_display_name=None,
        skills=[SkillSeedRow("a", "A", "cat", None, False)],
        languages=[
            LanguageSeedRow("dutch", "Dutch", "Speaking: x"),
            LanguageSeedRow("english", "English", "Speaking: x"),
            LanguageSeedRow("spanish", "Spanish", "Speaking: x"),
            LanguageSeedRow("german", "German", "Speaking: x"),
            LanguageSeedRow("french", "French", "Speaking: x"),
        ],
        countries=countries,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_valid_minimal_seed_has_no_errors() -> None:
    assert validate_seed(_minimal_seed()) == []


def test_wrong_language_count() -> None:
    seed = _minimal_seed(
        languages=[LanguageSeedRow("dutch", "Dutch", "Speaking: x")]
    )
    errors = validate_seed(seed)
    assert any("5 language" in e for e in errors)


def test_wrong_country_count() -> None:
    seed = _minimal_seed(countries=[CountrySeedRow("Only", None)])
    errors = validate_seed(seed)
    assert any("31 country" in e for e in errors)


def test_duplicate_skill_key() -> None:
    seed = _minimal_seed(
        skills=[
            SkillSeedRow("dup", "One", "cat", None, False),
            SkillSeedRow("dup", "Two", "cat", None, False),
        ]
    )
    errors = validate_seed(seed)
    assert any("Duplicate skill key" in e for e in errors)
