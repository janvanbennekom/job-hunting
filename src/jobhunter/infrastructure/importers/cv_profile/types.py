"""Parsed CV profile seed structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SkillSeedRow:
    key: str
    name: str
    category: str
    description: str | None
    cv_emphasized: bool


@dataclass(slots=True)
class LanguageSeedRow:
    key: str
    language: str
    proficiency_text: str


@dataclass(slots=True)
class CountrySeedRow:
    country: str
    notes: str | None


@dataclass(slots=True)
class CvProfileSeed:
    schema_version: int
    source_reference: str
    document_title: str
    document_version_label: str | None
    profile_display_name: str | None
    skills: list[SkillSeedRow]
    languages: list[LanguageSeedRow]
    countries: list[CountrySeedRow]
