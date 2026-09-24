"""Mapping serialization for domain models (stdlib-only)."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any


def enum_to_value(value: StrEnum) -> str:
    return value.value


def value_to_enum(enum_cls: type[StrEnum], raw: str) -> StrEnum:
    return enum_cls(raw)


def serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def deserialize_datetime(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def serialize_date(value: date) -> str:
    return value.isoformat()


def deserialize_date(raw: str) -> date:
    return date.fromisoformat(raw)


def serialize_optional_date(value: date | None) -> str | None:
    if value is None:
        return None
    return serialize_date(value)


def deserialize_optional_date(raw: str | None) -> date | None:
    if raw is None:
        return None
    return deserialize_date(raw)


def prune_none(mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: val for key, val in mapping.items() if val is not None}
