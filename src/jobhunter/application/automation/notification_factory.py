"""Resolve notification sender from application settings."""

from __future__ import annotations

from jobhunter.application.automation.notification import (
    ConsoleNotificationSender,
    NotificationSender,
)
from jobhunter.application.automation.smtp_notification import SmtpNotificationSender
from jobhunter.infrastructure.config import Settings


def resolve_notification_sender(settings: Settings) -> NotificationSender:
    """Production: SMTP when fully configured; otherwise console (dev / logs)."""
    if settings.smtp_configured():
        return SmtpNotificationSender(
            host=settings.smtp_host or "",
            port=settings.smtp_port or 587,
            username=settings.smtp_username,
            password=settings.smtp_password,
            mail_from=settings.smtp_from or "",
            mail_to=settings.smtp_to or "",
            use_ssl=settings.smtp_use_ssl,
            starttls=settings.smtp_starttls,
        )
    return ConsoleNotificationSender()
