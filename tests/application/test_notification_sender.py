"""Notification sender resolution tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from jobhunter.application.automation.notification import ConsoleNotificationSender
from jobhunter.application.automation.notification_factory import (
    resolve_notification_sender,
)
from jobhunter.application.automation.smtp_notification import SmtpNotificationSender
from jobhunter.infrastructure.config import Settings


def test_production_requires_smtp_when_notifications_expected() -> None:
    settings = Settings(
        env="production",
        log_level="INFO",
        database_url=None,
        openai_api_key=None,
        openai_model=None,
    )
    import pytest

    with pytest.raises(RuntimeError, match="Production notification"):
        resolve_notification_sender(settings, require_smtp_in_production=True)


def test_production_uses_smtp_when_ready() -> None:
    settings = Settings(
        env="production",
        log_level="INFO",
        database_url=None,
        openai_api_key=None,
        openai_model=None,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_from="jobhunter@example.com",
        smtp_to="user@example.com",
        smtp_username="smtp-user",
        smtp_password="secret",
    )
    sender = resolve_notification_sender(settings, require_smtp_in_production=True)
    assert isinstance(sender, SmtpNotificationSender)


def test_resolve_console_when_smtp_incomplete() -> None:
    settings = Settings(
        env="test",
        log_level="INFO",
        database_url=None,
        openai_api_key=None,
        openai_model=None,
    )
    sender = resolve_notification_sender(settings)
    assert isinstance(sender, ConsoleNotificationSender)


def test_resolve_smtp_when_configured() -> None:
    settings = Settings(
        env="test",
        log_level="INFO",
        database_url=None,
        openai_api_key=None,
        openai_model=None,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_from="jobhunter@example.com",
        smtp_to="user@example.com",
    )
    sender = resolve_notification_sender(settings)
    assert isinstance(sender, SmtpNotificationSender)


@patch("jobhunter.application.automation.smtp_notification.smtplib.SMTP")
def test_smtp_send_does_not_log_password(mock_smtp_class) -> None:
    client = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = client
    sender = SmtpNotificationSender(
        host="smtp.example.com",
        port=587,
        username="user",
        password="secret-password",
        mail_from="from@example.com",
        mail_to="to@example.com",
        starttls=True,
    )
    from jobhunter.application.automation.notification import (
        AutomationNotificationSummary,
    )

    summary = AutomationNotificationSummary(
        automation_run_id="run-1",
        trigger_type="MANUAL",
        dry_run=False,
        source_lines=["fao: ok"],
    )
    sender.send(summary)
    client.login.assert_called_once_with("user", "secret-password")
