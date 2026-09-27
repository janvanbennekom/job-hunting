"""Resolve notification sender from application settings."""

from __future__ import annotations

from jobhunter.application.automation.notification import (
    ConsoleNotificationSender,
    NotificationSender,
)
from jobhunter.application.automation.smtp_notification import SmtpNotificationSender
from jobhunter.infrastructure.config import Settings


_PRODUCTION_SMTP_ERROR = (
    "Production notification delivery requires SMTP. Set JOBHUNTER_SMTP_HOST, "
    "JOBHUNTER_SMTP_PORT, JOBHUNTER_SMTP_FROM, JOBHUNTER_SMTP_TO, and "
    "JOBHUNTER_SMTP_PASSWORD when JOBHUNTER_SMTP_USER is set."
)


def resolve_notification_sender(
    settings: Settings,
    *,
    require_smtp_in_production: bool = False,
) -> NotificationSender:
    """Resolve sender: SMTP when configured; otherwise console (development only).

    When ``require_smtp_in_production`` is True and ``settings.is_production()``,
    missing SMTP raises ``RuntimeError`` instead of falling back to console.
    """
    if require_smtp_in_production and settings.is_production():
        if not settings.smtp_production_ready():
            raise RuntimeError(_PRODUCTION_SMTP_ERROR)
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
