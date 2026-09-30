"""Operator relevance queue views (Phase 17G-2B)."""

from __future__ import annotations

from enum import StrEnum


class RelevanceQueueView(StrEnum):
    PRIMARY = "primary"
    WEAK = "weak"
    OUT_OF_SCOPE = "out_of_scope"
    NEEDS_REVIEW = "needs_review"
