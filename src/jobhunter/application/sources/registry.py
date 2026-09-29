"""Connector registry metadata for operational source UI (extensible)."""

from __future__ import annotations

from dataclasses import dataclass

from jobhunter.infrastructure.automation.config import (
    KNOWN_SOURCE_KEYS,
    SOURCE_KEY_TO_JOB_SOURCE_ID,
)


@dataclass(frozen=True, slots=True)
class SourceConnectorMeta:
    source_key: str
    connector_label: str
    default_display_name: str


_REGISTRY: tuple[SourceConnectorMeta, ...] = (
    SourceConnectorMeta("fao", "FAO", "FAO Jobs"),
    SourceConnectorMeta(
        "developmentaid", "DevelopmentAid", "DevelopmentAid Jobs"
    ),
    SourceConnectorMeta(
        "worldbank", "World Bank", "World Bank Procurement Notices"
    ),
    SourceConnectorMeta("undp", "UNDP", "UNDP Jobs"),
    SourceConnectorMeta("afdb", "AfDB", "AfDB Consultant Opportunities"),
)


def list_registered_connectors() -> tuple[SourceConnectorMeta, ...]:
    """All connectors known to the application (not only automation.json entries)."""
    return _REGISTRY


def connector_meta_for_key(source_key: str) -> SourceConnectorMeta | None:
    for item in _REGISTRY:
        if item.source_key == source_key:
            return item
    return None


def registered_source_keys() -> frozenset[str]:
    return KNOWN_SOURCE_KEYS


def job_source_id_for_key(source_key: str) -> str | None:
    return SOURCE_KEY_TO_JOB_SOURCE_ID.get(source_key)
