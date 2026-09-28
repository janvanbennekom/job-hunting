"""Pursuit / application workflow status (Phase 14 — not review triage)."""

from __future__ import annotations

from enum import StrEnum


class PursuitStatus(StrEnum):
    """Consultancy pursuit stages after explicit human decision to pursue.

    CLIENT_SHORTLISTED means the client/procurement shortlist — not the
    dashboard review disposition ``SHORTLIST``.
    """

    CONSIDERING = "CONSIDERING"
    PREPARING = "PREPARING"
    SUBMITTED = "SUBMITTED"
    CLIENT_SHORTLISTED = "CLIENT_SHORTLISTED"
    INTERVIEW = "INTERVIEW"
    NEGOTIATION = "NEGOTIATION"
    AWARDED = "AWARDED"
    NOT_AWARDED = "NOT_AWARDED"
    WITHDRAWN = "WITHDRAWN"


TERMINAL_PURSUIT_STATUSES = frozenset(
    {
        PursuitStatus.AWARDED,
        PursuitStatus.NOT_AWARDED,
        PursuitStatus.WITHDRAWN,
    }
)
