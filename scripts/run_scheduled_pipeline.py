"""Run the JobHunter scheduled automation pipeline once (Phase 13)."""

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
        description="Run multi-source acquisition and downstream pipeline once."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and adapters without persisting",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist scans, processing, optional assessment/ranking, and notify",
    )
    parser.add_argument(
        "--apply-if-due",
        action="store_true",
        help="Run --apply only when schedule says the current minute is due",
    )
    parser.add_argument(
        "--check-schedule",
        action="store_true",
        help="Print whether the configured schedule is due now and exit",
    )
    parser.add_argument(
        "--trigger",
        choices=("manual", "scheduled"),
        default="manual",
        help="Recorded trigger type when --apply is used",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Automation JSON config (default: JOBHUNTER_AUTOMATION_CONFIG or built-in defaults)",
    )
    args = parser.parse_args(argv)

    if not args.dry_run and not args.apply and not args.apply_if_due and not args.check_schedule:
        parser.error("Specify --dry-run, --apply, --apply-if-due, or --check-schedule")

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    from jobhunter.application.automation.notification_factory import (
        resolve_notification_sender,
    )
    from jobhunter.application.automation.notification_observability import (
        report_notification_sender,
    )
    from jobhunter.application.automation.pipeline import ScheduledPipelineOrchestrator
    from jobhunter.application.automation.schedule import is_schedule_due
    from jobhunter.domain.automation_enums import AutomationTriggerType
    from jobhunter.infrastructure.automation.config import load_automation_config
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    config = load_automation_config(path=args.config)

    if args.check_schedule:
        due = is_schedule_due(config.schedule)
        print(f"schedule.enabled={config.schedule.enabled} due_now={due}")
        return 0 if due or not config.schedule.enabled else 1

    if args.apply_if_due:
        settings = get_settings()
        settings.require_database_url()
        engine = create_engine_from_settings(settings)
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            if not is_schedule_due(config.schedule, session=session):
                print("Schedule not due; skipping run.")
                return 0
        args.apply = True
        args.trigger = "scheduled"

    apply = bool(args.apply)
    if apply:
        settings = get_settings()
        settings.require_database_url()

    trigger = (
        AutomationTriggerType.SCHEDULED
        if args.trigger == "scheduled"
        else AutomationTriggerType.MANUAL
    )

    if apply:
        engine = create_engine_from_settings()
        session_factory = create_session_factory(engine)
        needs_sender = (
            config.notifications.enabled
            or config.notifications.high_ranking_alerts_enabled
        )
        sender = None
        if needs_sender:
            sender = resolve_notification_sender(
                settings,
                require_smtp_in_production=True,
            )
        report_notification_sender(sender, needs_sender=needs_sender)
        from jobhunter.application.automation.worker_lock import WorkerAutomationLock

        from jobhunter.application.automation.pipeline_progress import (
            pipeline_starting,
        )

        with session_scope(session_factory) as session:
            lock = WorkerAutomationLock(session)
            if not lock.try_acquire():
                print(
                    "Another worker holds the JobHunter automation lock; skipping."
                )
                return 0
            try:
                pipeline_starting(apply=True, trigger=trigger.value)
                orchestrator = ScheduledPipelineOrchestrator(
                    session,
                    config,
                    notification_sender=sender,
                )
                result = orchestrator.run(apply=True, trigger_type=trigger)
            finally:
                lock.release()
    else:
        settings = get_settings()
        settings.require_database_url()
        engine = create_engine_from_settings()
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            orchestrator = ScheduledPipelineOrchestrator(session, config)
            result = orchestrator.run(apply=False, trigger_type=trigger)
        if result.notification is not None:
            print(result.notification.render_text())

    if result.automation_run is not None:
        print(
            f"AutomationRun {result.automation_run.id} "
            f"status={result.automation_run.status.value}"
        )
    for line in _summary_lines(result):
        print(line)
    return result.exit_code


def _summary_lines(result) -> list[str]:
    lines = [
        f"dry_run={result.dry_run}",
        f"sources={len(result.source_results)}",
    ]
    if result.assessment is not None:
        if result.assessment.skipped:
            lines.append(f"assessment_skipped={result.assessment.skip_reason}")
        else:
            lines.append(
                f"assessment assessed={result.assessment.assessed} "
                f"reused={result.assessment.reused}"
            )
    if result.ranking_attempted:
        lines.append(
            f"ranking attempted={result.ranking_attempted} "
            f"ranked={result.ranking_ranked} unranked={result.ranking_unranked}"
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
