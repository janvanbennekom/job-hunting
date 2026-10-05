"""Orchestrate multi-source scheduled automation (Phase 13)."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy.orm import Session

from jobhunter.application.automation.assessment_batch import (
    AssessmentBatchResult,
    AssessmentModelFactory,
    run_production_assessment_batch,
)
from jobhunter.application.automation.notification import (
    AutomationNotificationBuilder,
    AutomationNotificationSummary,
    NotificationSender,
)
from jobhunter.application.automation.notification_observability import (
    deliver_automation_summary,
    report_summary_skipped_notifications_disabled,
)
from jobhunter.application.automation.high_ranking_alerts import (
    HighRankingAlertService,
)
from jobhunter.application.automation.pipeline_progress import (
    phase_completed,
    phase_starting,
    pipeline_completed,
    source_completed,
    source_failed,
    source_starting,
)
from jobhunter.application.automation.source_adapters import (
    SourceAdapterResult,
    SourceScanAdapter,
    default_source_adapters,
    get_adapter,
)
from jobhunter.application.ranking import OpportunityRankingService
from jobhunter.application.ranking.service import RankingOutcome
from jobhunter.domain.automation_enums import (
    AutomationRunStatus,
    AutomationTriggerType,
)
from jobhunter.domain.automation_run import AutomationRun
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.automation.config import AutomationConfig
from jobhunter.infrastructure.config import Settings, get_settings
from jobhunter.infrastructure.persistence.automation_run_repository import (
    AutomationRunRepository,
)


@dataclass(slots=True)
class PipelineRunResult:
    dry_run: bool
    automation_run: AutomationRun | None
    source_results: list[SourceAdapterResult] = field(default_factory=list)
    assessment: AssessmentBatchResult | None = None
    ranking_attempted: int = 0
    ranking_ranked: int = 0
    ranking_unranked: int = 0
    notification: AutomationNotificationSummary | None = None
    high_ranking_alerts_sent: int = 0
    high_ranking_alerts_failed: int = 0
    warnings: list[str] = field(default_factory=list)
    exit_code: int = 0


class ScheduledPipelineOrchestrator:
    def __init__(
        self,
        session: Session,
        config: AutomationConfig,
        *,
        settings: Settings | None = None,
        adapters: dict[str, SourceScanAdapter] | None = None,
        notification_sender: NotificationSender | None = None,
        assessment_model_factory: AssessmentModelFactory | None = None,
    ) -> None:
        self._session = session
        self._config = config
        self._settings = settings or get_settings()
        self._adapters = adapters or default_source_adapters()
        self._runs = AutomationRunRepository(session)
        self._notification_sender = notification_sender
        self._assessment_model_factory = assessment_model_factory

    def run(
        self,
        *,
        apply: bool,
        trigger_type: AutomationTriggerType = AutomationTriggerType.MANUAL,
    ) -> PipelineRunResult:
        started = datetime.now(timezone.utc)
        warnings: list[str] = []
        source_results: list[SourceAdapterResult] = []
        run_entity: AutomationRun | None = None

        run_profile_in_scan = False
        assess_in_pipeline = self._config.pipeline.production_assessment_enabled

        if apply:
            run_entity = AutomationRun(
                started_at=started,
                trigger_type=trigger_type,
                status=AutomationRunStatus.RUNNING,
                config_snapshot=self._config.sanitized_snapshot(),
            )
            run_entity = self._runs.save(run_entity)
            self._session.commit()

        all_processed: list[str] = []
        all_new: list[str] = []
        all_updated: list[str] = []

        for source_cfg in self._config.enabled_sources():
            source_started = perf_counter()
            try:
                adapter = get_adapter(source_cfg.key, self._adapters)
            except KeyError as exc:
                duration = perf_counter() - source_started
                source_failed(
                    source_cfg.key,
                    duration_seconds=duration,
                    error=str(exc),
                )
                result = SourceAdapterResult(
                    source_key=source_cfg.key,
                    source_id="",
                    source_scan_id=None,
                    scan_status=None,
                    error_message=str(exc),
                )
                source_results.append(result)
                if apply:
                    self._session.commit()
                continue

            source_starting(source_cfg.key)
            try:
                result = adapter.run(
                    self._session,
                    source_cfg,
                    apply=apply,
                    run_profile_assessment=run_profile_in_scan and not assess_in_pipeline,
                )
            except (TimeoutError, socket.timeout) as exc:
                duration = perf_counter() - source_started
                source_failed(
                    source_cfg.key,
                    duration_seconds=duration,
                    error=str(exc),
                    kind="TIMEOUT",
                )
                result = SourceAdapterResult(
                    source_key=source_cfg.key,
                    source_id="",
                    source_scan_id=None,
                    scan_status=SourceScanStatus.FAILED,
                    error_message=str(exc),
                )
            except Exception as exc:  # noqa: BLE001
                duration = perf_counter() - source_started
                source_failed(
                    source_cfg.key,
                    duration_seconds=duration,
                    error=str(exc),
                )
                result = SourceAdapterResult(
                    source_key=source_cfg.key,
                    source_id="",
                    source_scan_id=None,
                    scan_status=SourceScanStatus.FAILED,
                    error_message=str(exc),
                )
            else:
                duration = perf_counter() - source_started
                if result.error_message:
                    source_failed(
                        source_cfg.key,
                        duration_seconds=duration,
                        error=result.error_message,
                    )
                else:
                    source_completed(
                        source_cfg.key,
                        duration_seconds=duration,
                        retrieved=result.retrieved,
                        processed=result.processed,
                    )
            source_results.append(result)
            if apply:
                self._session.commit()
            if result.error_message:
                continue
            all_processed.extend(result.processed_opportunity_ids)
            all_new.extend(result.new_opportunity_ids)
            all_updated.extend(result.materially_updated_opportunity_ids)

        assessment_result: AssessmentBatchResult | None = None
        if apply and assess_in_pipeline and all_processed:
            phase_starting("assessment batch")
            try:
                assessment_result = run_production_assessment_batch(
                    self._session,
                    all_processed,
                    settings=self._settings,
                    required=self._config.pipeline.assessment_required,
                    model_factory=self._assessment_model_factory,
                )
            except RuntimeError as exc:
                warnings.append(str(exc))
                assessment_result = AssessmentBatchResult(
                    skipped=True, skip_reason=str(exc)
                )
            if assessment_result is not None:
                if assessment_result.skipped:
                    phase_completed(
                        "assessment batch",
                        skipped=assessment_result.skip_reason or "true",
                    )
                else:
                    phase_completed(
                        "assessment batch",
                        assessed=assessment_result.assessed,
                        reused=assessment_result.reused,
                    )
            if apply:
                self._session.commit()
        elif not apply and assess_in_pipeline:
            warnings.append(
                "production_assessment_enabled: would run after scans (dry-run)"
            )

        ranking_attempted = 0
        ranking_ranked = 0
        ranking_unranked = 0
        ranking_outcomes: list[RankingOutcome] = []
        if apply and self._config.pipeline.ranking_enabled and all_processed:
            phase_starting("ranking")
            ranking_service = OpportunityRankingService(self._session)
            unique_ids = _unique_preserve_order(all_processed)
            ranking_attempted = len(unique_ids)
            for opp_id in unique_ids:
                try:
                    outcome = ranking_service.rank_opportunity(
                        opp_id,
                        include_fake_assessments=False,
                    )
                    ranking_outcomes.append(outcome)
                    if outcome.ranking.status.value == "RANKED":
                        ranking_ranked += 1
                    else:
                        ranking_unranked += 1
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"ranking {opp_id}: {exc}")
                    ranking_unranked += 1
            phase_completed(
                "ranking",
                attempted=ranking_attempted,
                ranked=ranking_ranked,
                unranked=ranking_unranked,
            )
            if apply:
                self._session.commit()
        elif not apply and self._config.pipeline.ranking_enabled:
            warnings.append("ranking_enabled: would rank processed opportunities (dry-run)")

        high_alerts_sent = 0
        high_alerts_failed = 0
        if (
            apply
            and self._config.notifications.high_ranking_alerts_enabled
            and ranking_outcomes
            and self._notification_sender is not None
        ):
            phase_starting("high-ranking notifications")
            alert_service = HighRankingAlertService(self._session, self._settings)
            alert_result = alert_service.process_ranking_outcomes(
                ranking_outcomes,
                sender=self._notification_sender,
            )
            high_alerts_sent = alert_result.sent
            high_alerts_failed = alert_result.failed
            for err in alert_result.errors:
                warnings.append(f"high_ranking_alert: {err}")
            phase_completed(
                "high-ranking notifications",
                sent=high_alerts_sent,
                failed=high_alerts_failed,
            )
            if apply:
                self._session.commit()

        if apply and run_entity is not None:
            run_entity = self._finalize_run(
                run_entity,
                source_results,
                warnings,
                completed_at=datetime.now(timezone.utc),
            )
            run_entity = self._runs.save(run_entity)

        notification_summary: AutomationNotificationSummary | None = None
        if self._config.notifications.enabled or not apply:
            builder = AutomationNotificationBuilder(self._session)
            notification_summary = builder.build(
                automation_run=run_entity,
                trigger_type=trigger_type.value,
                dry_run=not apply,
                source_results=source_results,
                assessment=assessment_result,
                ranking_enabled=self._config.pipeline.ranking_enabled,
                processed_ids=_unique_preserve_order(all_processed),
                new_ids=_unique_preserve_order(all_new),
                updated_ids=_unique_preserve_order(all_updated),
                warnings=warnings,
            )
            phase_starting("run summary notification")
            deliver_automation_summary(
                self._notification_sender,
                notification_summary,
                apply=apply,
                notifications_enabled=self._config.notifications.enabled,
            )
            phase_completed("run summary notification")
            if apply:
                self._session.commit()
        elif apply:
            report_summary_skipped_notifications_disabled()

        exit_code = _compute_exit_code(source_results, run_entity)
        pipeline_completed(exit_code=exit_code, run_id=run_entity.id if run_entity else None)
        return PipelineRunResult(
            dry_run=not apply,
            automation_run=run_entity,
            source_results=source_results,
            assessment=assessment_result,
            ranking_attempted=ranking_attempted,
            ranking_ranked=ranking_ranked,
            ranking_unranked=ranking_unranked,
            notification=notification_summary,
            high_ranking_alerts_sent=high_alerts_sent,
            high_ranking_alerts_failed=high_alerts_failed,
            warnings=warnings,
            exit_code=exit_code,
        )

    def _finalize_run(
        self,
        run: AutomationRun,
        source_results: list[SourceAdapterResult],
        warnings: list[str],
        *,
        completed_at: datetime,
    ) -> AutomationRun:
        scan_ids: list[str] = []
        retrieved = processed = failed = 0
        sources_ok = 0
        sources_bad = 0
        for result in source_results:
            if result.error_message:
                sources_bad += 1
                continue
            sources_ok += 1
            if result.source_scan_id:
                scan_ids.append(result.source_scan_id)
            retrieved += result.retrieved
            processed += result.processed
            failed += result.failed

        status = _resolve_run_status(source_results, warnings)
        error_parts = [
            r.error_message for r in source_results if r.error_message
        ] + warnings
        error_summary = _build_error_summary(error_parts)

        run.completed_at = completed_at
        run.status = status
        run.source_scan_ids = scan_ids
        run.records_retrieved = retrieved
        run.records_processed = processed
        run.records_failed = failed
        run.sources_succeeded = sources_ok
        run.sources_failed = sources_bad
        run.error_summary = error_summary
        return run


def _unique_preserve_order(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in ids:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _resolve_run_status(
    source_results: list[SourceAdapterResult],
    warnings: list[str],
) -> AutomationRunStatus:
    if not source_results:
        return AutomationRunStatus.FAILED
    hard_failures = sum(1 for r in source_results if r.error_message)
    partial_scans = sum(
        1
        for r in source_results
        if not r.error_message
        and r.scan_status in (SourceScanStatus.PARTIAL, SourceScanStatus.FAILED)
    )
    if hard_failures == len(source_results):
        return AutomationRunStatus.FAILED
    if hard_failures > 0 or partial_scans > 0 or warnings:
        return AutomationRunStatus.PARTIAL
    return AutomationRunStatus.SUCCESS


def _compute_exit_code(
    source_results: list[SourceAdapterResult],
    run: AutomationRun | None,
) -> int:
    if run is None:
        return 0
    if run.status is AutomationRunStatus.FAILED:
        return 2
    if run.status is AutomationRunStatus.PARTIAL:
        return 1
    return 0


def _build_error_summary(parts: list[str]) -> str | None:
    if not parts:
        return None
    head = parts[:8]
    summary = "; ".join(head)
    if len(parts) > 8:
        summary += f"; … and {len(parts) - 8} more"
    return summary[:4000]
