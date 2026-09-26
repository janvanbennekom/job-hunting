"""Human review dispositions (Phase 10)."""

from __future__ import annotations

from enum import StrEnum


class ReviewDisposition(StrEnum):
    SHORTLIST = "SHORTLIST"
    INVESTIGATE = "INVESTIGATE"
    DISMISS = "DISMISS"
