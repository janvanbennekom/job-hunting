"""Load curated Professional Services JSON seed."""

from __future__ import annotations

import json
from pathlib import Path

from jobhunter.infrastructure.importers.professional_services.types import (
    ProfessionalServicesSeed,
    ServiceSeedRow,
)


def load_seed(path: Path) -> ProfessionalServicesSeed:
    data = json.loads(path.read_text(encoding="utf-8"))
    profile = data.get("professional_profile") or {}
    doc = data.get("source_document") or {}
    services: list[ServiceSeedRow] = []
    for item in data.get("services") or []:
        services.append(
            ServiceSeedRow(
                key=str(item["key"]).strip(),
                name=str(item["name"]).strip(),
                description=(
                    str(item["description"]).strip() if item.get("description") else None
                ),
                is_active=bool(item.get("is_active", True)),
            )
        )
    return ProfessionalServicesSeed(
        schema_version=int(data.get("schema_version", 1)),
        source_reference=str(data["source_reference"]).strip(),
        document_title=str(doc.get("title", "Professional Services")).strip(),
        document_version_label=(
            str(doc["version_label"]).strip() if doc.get("version_label") else None
        ),
        profile_display_name=str(profile["display_name"]).strip(),
        profile_positioning_summary=(
            str(profile["positioning_summary"]).strip()
            if profile.get("positioning_summary")
            else None
        ),
        services=services,
    )
