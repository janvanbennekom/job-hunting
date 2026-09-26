"""Unit tests for country experience deterministic identity."""

from jobhunter.infrastructure.importers.country_experience_identity import (
    country_experience_id,
    normalize_country_name,
)


def test_normalize_country_name_collapses_whitespace_and_case() -> None:
    assert normalize_country_name("  The   Netherlands ") == "the netherlands"
    assert normalize_country_name("Ghana") == "ghana"


def test_country_experience_id_is_stable_per_source_and_country() -> None:
    ref = "docs/cv_example.pdf"
    assert country_experience_id(ref, "Ghana") == country_experience_id(ref, "Ghana")
    assert country_experience_id(ref, "Ghana") == country_experience_id(ref, "  ghana ")
    assert country_experience_id(ref, "Ghana") != country_experience_id(ref, "Kenya")
    assert country_experience_id(ref, "Ghana") != country_experience_id(
        "docs/other.pdf", "Ghana"
    )
