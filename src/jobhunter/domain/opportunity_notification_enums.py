"""Enumerations for opportunity notification audit records."""

from __future__ import annotations

from enum import StrEnum


class OpportunityNotificationType(StrEnum):
    HIGH_RANKING = "HIGH_RANKING"


class OpportunityNotificationChannel(StrEnum):
    CONSOLE = "CONSOLE"
    SMTP = "SMTP"


class OpportunityNotificationStatus(StrEnum):
    SENT = "SENT"
    FAILED = "FAILED"
