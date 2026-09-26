"""Load curated search strategy JSON seed."""

from __future__ import annotations

import json
from pathlib import Path

from jobhunter.infrastructure.importers.search_strategy.types import (
    CriterionSeedRow,
    ExclusionSeedRow,
    SearchStrategySeed,
    ThemeSeedRow,
)


def load_seed(path: Path) -> SearchStrategySeed:
    data = json.loads(path.read_text(encoding="utf-8"))
    themes = [
        ThemeSeedRow(
            key=str(item["key"]).strip(),
            label=str(item["label"]).strip(),
            strength=str(item["strength"]).strip(),
            is_active=bool(item.get("is_active", True)),
            notes=str(item["notes"]).strip() if item.get("notes") else None,
            sort_order=int(item.get("sort_order", 0)),
        )
        for item in data.get("themes") or []
    ]
    criteria = [
        CriterionSeedRow(
            category=str(item["category"]).strip(),
            code=str(item["code"]).strip(),
            value=dict(item["value"]),
            strength=(
                str(item["strength"]).strip() if item.get("strength") else None
            ),
            is_active=bool(item.get("is_active", True)),
            notes=str(item["notes"]).strip() if item.get("notes") else None,
            sort_order=int(item.get("sort_order", 0)),
        )
        for item in data.get("criteria") or []
    ]
    exclusions = [
        ExclusionSeedRow(
            exclusion_code=str(item["exclusion_code"]).strip(),
            parameters=(
                dict(item["parameters"]) if item.get("parameters") else None
            ),
            is_active=bool(item.get("is_active", True)),
            notes=str(item["notes"]).strip() if item.get("notes") else None,
        )
        for item in data.get("exclusions") or []
    ]
    return SearchStrategySeed(
        schema_version=int(data.get("schema_version", 1)),
        owner_key=str(data["owner_key"]).strip(),
        change_summary=str(data["change_summary"]).strip(),
        change_source=str(data["change_source"]).strip(),
        themes=themes,
        criteria=criteria,
        exclusions=exclusions,
    )
