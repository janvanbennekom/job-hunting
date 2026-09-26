"""Validate CV profile seed before apply."""

from __future__ import annotations

from collections import Counter

from jobhunter.infrastructure.importers.cv_profile.types import CvProfileSeed


def validate_seed(seed: CvProfileSeed) -> list[str]:
    errors: list[str] = []

    if seed.schema_version != 1:
        errors.append(f"Unsupported schema_version {seed.schema_version}")

    if not seed.source_reference:
        errors.append("source_reference is required")

    if not seed.document_title:
        errors.append("source_document.title is required")

    for key, count in Counter(s.key for s in seed.skills).items():
        if not key:
            errors.append("Skill key must be non-empty")
        elif count > 1:
            errors.append(f"Duplicate skill key: {key}")

    for row in seed.skills:
        if not row.name:
            errors.append(f"Skill {row.key!r}: name is required")
        if not row.category:
            errors.append(f"Skill {row.key!r}: category is required")

    for key, count in Counter(l.key for l in seed.languages).items():
        if not key:
            errors.append("Language key must be non-empty")
        elif count > 1:
            errors.append(f"Duplicate language key: {key}")

    for row in seed.languages:
        if not row.language:
            errors.append(f"Language {row.key!r}: language is required")
        if not row.proficiency_text:
            errors.append(f"Language {row.key!r}: proficiency_text is required")

    countries = [c.country for c in seed.countries]
    for country, count in Counter(countries).items():
        if not country:
            errors.append("Country name must be non-empty")
        elif count > 1:
            errors.append(f"Duplicate country: {country}")

    if not seed.skills:
        errors.append("At least one skill is required")

    if len(seed.languages) != 5:
        errors.append(f"Expected 5 language records, found {len(seed.languages)}")

    if len(seed.countries) != 31:
        errors.append(f"Expected 31 country records, found {len(seed.countries)}")

    return errors
