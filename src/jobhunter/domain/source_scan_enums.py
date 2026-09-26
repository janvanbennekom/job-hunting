"""Enumerations for source scan runs."""

from __future__ import annotations

from enum import StrEnum


class SourceScanStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
