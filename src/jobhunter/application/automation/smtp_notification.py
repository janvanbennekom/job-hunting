"""SMTP notification delivery for automation summaries."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from jobhunter.application.automation.notification import (
    AutomationNotificationSummary,
    NotificationSender,
)


class SmtpNotificationSender(NotificationSender):
    """Send automation summaries via generic SMTP (credentials from env only)."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        mail_from: str,
        mail_to: str,
        use_ssl: bool = False,
        starttls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._mail_from = mail_from
        self._mail_to = mail_to
        self._use_ssl = use_ssl
        self._starttls = starttls

    def send(self, summary: AutomationNotificationSummary) -> None:
        body = summary.render_text()
        subject = "JobHunter automation summary"
        if summary.dry_run:
            subject += " (dry-run)"

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._mail_from
        message["To"] = self._mail_to
        message.set_content(body)

        if self._use_ssl:
            with smtplib.SMTP_SSL(self._host, self._port, timeout=60) as client:
                self._login(client)
                client.send_message(message)
            return

        with smtplib.SMTP(self._host, self._port, timeout=60) as client:
            if self._starttls:
                client.starttls()
            self._login(client)
            client.send_message(message)

    def _login(self, client: smtplib.SMTP) -> None:
        if self._username and self._password:
            client.login(self._username, self._password)
