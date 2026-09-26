"""Parsed professional services seed structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ServiceSeedRow:
    key: str
    name: str
    description: str | None
    is_active: bool


@dataclass(slots=True)
class ProfessionalServicesSeed:
    schema_version: int
    source_reference: str
    document_title: str
    document_version_label: str | None
    profile_display_name: str
    profile_positioning_summary: str | None
    services: list[ServiceSeedRow]
