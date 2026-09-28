"""Send a labelled JobHunter SMTP test message (no scans, OpenAI, or DB writes)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    import os

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Send a JobHunter SMTP connectivity test email."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate SMTP settings without sending",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    from jobhunter.application.automation.notification import (
        AutomationNotificationSummary,
    )
    from jobhunter.application.automation.notification_factory import (
        resolve_notification_sender,
    )
    from jobhunter.infrastructure.config import get_settings

    settings = get_settings()
    if settings.is_production():
        resolve_notification_sender(settings, require_smtp_in_production=True)
    elif not settings.smtp_production_ready() and not settings.smtp_configured():
        print(
            "SMTP is not configured. Set JOBHUNTER_SMTP_* in .env before testing.",
            file=sys.stderr,
        )
        return 1

    sender = resolve_notification_sender(
        settings,
        require_smtp_in_production=settings.is_production(),
    )

    summary = AutomationNotificationSummary(
        automation_run_id=None,
        trigger_type="SMTP_TEST",
        dry_run=False,
        source_lines=[
            "JobHunter SMTP test — this is not a scan result.",
            "If you received this, production notification delivery is configured.",
        ],
        warnings=[],
    )

    if args.dry_run:
        print("SMTP settings appear sufficient for notification delivery.")
        print(f"Sender type: {type(sender).__name__}")
        print(summary.render_text())
        return 0

    try:
        sender.send(summary)
    except Exception as exc:  # noqa: BLE001
        print(f"SMTP send failed: {exc}", file=sys.stderr)
        return 1

    print("SMTP test message sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
