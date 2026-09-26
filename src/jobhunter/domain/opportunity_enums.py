"""Enumerations for opportunity processing."""

from __future__ import annotations

from enum import StrEnum


class MaterialChangeField(StrEnum):
    """Normalized opportunity fields tracked for material change detection."""

    TITLE = "title"
    DEADLINE = "deadline"
    DESCRIPTION = "description"
    LOCATION = "location"
    SOURCE_STATUS = "source_status"
