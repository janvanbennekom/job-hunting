"""Stdout markers for automation summary delivery (no secrets)."""

from __future__ import annotations

from jobhunter.application.automation.notification import (
    AutomationNotificationSummary,
    NotificationSender,
)


def report_notification_sender(
    sender: object | None,
    *,
    needs_sender: bool,
) -> None:
    """Log resolved notification sender class after CLI resolution."""
    if not needs_sender:
        return
    name = type(sender).__name__ if sender is not None else "(none)"
    print(f"Notification sender: {name}")


def deliver_automation_summary(
    sender: NotificationSender | None,
    summary: AutomationNotificationSummary,
    *,
    apply: bool,
    notifications_enabled: bool,
) -> None:
    """Send run summary with explicit skip/success markers; exceptions propagate."""
    if not apply:
        print("Automation summary send skipped: dry-run")
        return
    if not notifications_enabled:
        print("Automation summary send skipped: notifications disabled")
        return
    if sender is None:
        print("Automation summary send skipped: no notification sender")
        return
    sender_name = type(sender).__name__
    print(f"Sending automation summary via {sender_name}...")
    sender.send(summary)
    print("Automation summary sent successfully.")


def report_summary_skipped_notifications_disabled() -> None:
    """When apply run does not build a summary because notifications are disabled."""
    print("Automation summary send skipped: notifications disabled")
