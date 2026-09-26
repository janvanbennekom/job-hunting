"""Load curated CV profile JSON seed."""

from __future__ import annotations

import json
from pathlib import Path

from jobhunter.infrastructure.importers.cv_profile.types import (
    CountrySeedRow,
    CvProfileSeed,
    LanguageSeedRow,
    SkillSeedRow,
)


def load_seed(path: Path) -> CvProfileSeed:
    data = json.loads(path.read_text(encoding="utf-8"))
    doc = data.get("source_document") or {}
    profile = data.get("professional_profile") or {}
    skills = [
        SkillSeedRow(
            key=str(item["key"]).strip(),
            name=str(item["name"]).strip(),
            category=str(item["category"]).strip(),
            description=(
                str(item["description"]).strip() if item.get("description") else None
            ),
            cv_emphasized=bool(item.get("cv_emphasized", False)),
        )
        for item in data.get("skills") or []
    ]
    languages = [
        LanguageSeedRow(
            key=str(item["key"]).strip(),
            language=str(item["language"]).strip(),
            proficiency_text=str(item["proficiency_text"]).strip(),
        )
        for item in data.get("languages") or []
    ]
    countries = [
        CountrySeedRow(
            country=str(item["country"]).strip(),
            notes=str(item["notes"]).strip() if item.get("notes") else None,
        )
        for item in data.get("countries") or []
    ]
    return CvProfileSeed(
        schema_version=int(data.get("schema_version", 1)),
        source_reference=str(data["source_reference"]).strip(),
        document_title=str(doc.get("title", "Curriculum Vitae")).strip(),
        document_version_label=(
            str(doc["version_label"]).strip() if doc.get("version_label") else None
        ),
        profile_display_name=(
            str(profile["display_name"]).strip() if profile.get("display_name") else None
        ),
        skills=skills,
        languages=languages,
        countries=countries,
    )
