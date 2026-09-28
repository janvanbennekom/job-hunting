"""Automation summary delivery observability (Phase 13)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from jobhunter.application.automation.notification import (
    AutomationNotificationSummary,
    ConsoleNotificationSender,
)
from jobhunter.application.automation.notification_observability import (
    deliver_automation_summary,
    report_notification_sender,
    report_summary_skipped_notifications_disabled,
)
from jobhunter.application.automation.smtp_notification import SmtpNotificationSender
from jobhunter.infrastructure.config import Settings


def test_report_notification_sender_smtp_class_only(capsys: pytest.CaptureFixture[str]) -> None:
    sender = SmtpNotificationSender(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secret",
        mail_from="from@example.com",
        mail_to="to@example.com",
    )
    report_notification_sender(sender, needs_sender=True)
    out = capsys.readouterr().out
    assert out.strip() == "Notification sender: SmtpNotificationSender"
    assert "smtp.example.com" not in out
    assert "secret" not in out
    assert "to@example.com" not in out


def test_report_notification_sender_omitted_when_not_needed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_notification_sender(None, needs_sender=False)
    assert capsys.readouterr().out == ""


def test_deliver_summary_success_messages(capsys: pytest.CaptureFixture[str]) -> None:
    sender = ConsoleNotificationSender()
    summary = AutomationNotificationSummary(
        automation_run_id="run-1",
        trigger_type="MANUAL",
        dry_run=False,
    )
    deliver_automation_summary(
        sender,
        summary,
        apply=True,
        notifications_enabled=True,
    )
    out = capsys.readouterr().out
    assert "Sending automation summary via ConsoleNotificationSender..." in out
    assert "Automation summary sent successfully." in out


def test_deliver_summary_skipped_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    sender = MagicMock()
    summary = AutomationNotificationSummary(
        automation_run_id=None,
        trigger_type="MANUAL",
        dry_run=True,
    )
    deliver_automation_summary(
        sender,
        summary,
        apply=False,
        notifications_enabled=True,
    )
    assert capsys.readouterr().out.strip() == (
        "Automation summary send skipped: dry-run"
    )
    sender.send.assert_not_called()


def test_deliver_summary_skipped_notifications_disabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sender = MagicMock()
    summary = AutomationNotificationSummary(
        automation_run_id="run-1",
        trigger_type="MANUAL",
        dry_run=False,
    )
    deliver_automation_summary(
        sender,
        summary,
        apply=True,
        notifications_enabled=False,
    )
    assert capsys.readouterr().out.strip() == (
        "Automation summary send skipped: notifications disabled"
    )
    sender.send.assert_not_called()


def test_deliver_summary_skipped_no_sender(capsys: pytest.CaptureFixture[str]) -> None:
    summary = AutomationNotificationSummary(
        automation_run_id="run-1",
        trigger_type="MANUAL",
        dry_run=False,
    )
    deliver_automation_summary(
        None,
        summary,
        apply=True,
        notifications_enabled=True,
    )
    assert capsys.readouterr().out.strip() == (
        "Automation summary send skipped: no notification sender"
    )


def test_deliver_summary_smtp_exception_propagates() -> None:
    sender = MagicMock()
    sender.send.side_effect = OSError("SMTP failure")
    summary = AutomationNotificationSummary(
        automation_run_id="run-1",
        trigger_type="MANUAL",
        dry_run=False,
    )
    with pytest.raises(OSError, match="SMTP failure"):
        deliver_automation_summary(
            sender,
            summary,
            apply=True,
            notifications_enabled=True,
        )
    sender.send.assert_called_once_with(summary)


def test_production_resolve_reports_smtp_sender_class_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from jobhunter.application.automation.notification_factory import (
        resolve_notification_sender,
    )

    settings = Settings.from_environ(
        {
            "JOBHUNTER_ENV": "production",
            "JOBHUNTER_SMTP_HOST": "smtp.example.com",
            "JOBHUNTER_SMTP_PORT": "587",
            "JOBHUNTER_SMTP_FROM": "from@example.com",
            "JOBHUNTER_SMTP_TO": "to@example.com",
            "JOBHUNTER_SMTP_USER": "user",
            "JOBHUNTER_SMTP_PASSWORD": "pass",
        }
    )
    sender = resolve_notification_sender(settings, require_smtp_in_production=True)
    report_notification_sender(sender, needs_sender=True)
    out = capsys.readouterr().out
    assert "Notification sender: SmtpNotificationSender" in out
    assert "pass" not in out
    assert "smtp.example.com" not in out


def test_report_summary_skipped_when_notifications_disabled_block(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_summary_skipped_notifications_disabled()
    assert capsys.readouterr().out.strip() == (
        "Automation summary send skipped: notifications disabled"
    )
