"""Notification abstraction and summary construction from persisted state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.application.automation.assessment_batch import AssessmentBatchResult
from jobhunter.application.automation.source_adapters import SourceAdapterResult
from jobhunter.domain.automation_run import AutomationRun
from jobhunter.domain.enums import EligibilityStatus
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.infrastructure.persistence.models import (
    OpportunityRow,
    OpportunitySourceRow,
)
from jobhunter.infrastructure.persistence.ranking_repositories import (
    OpportunityRankingRepository,
)


@dataclass(slots=True)
class OpportunityNotificationLine:
    opportunity_id: str
    title: str
    source_url: str | None
    eligibility_status: str | None
    ranking_status: str | None
    priority_band: str | None
    note: str | None = None


@dataclass(slots=True)
class AutomationNotificationSummary:
    automation_run_id: str | None
    trigger_type: str
    dry_run: bool
    source_lines: list[str] = field(default_factory=list)
    new_opportunities: list[OpportunityNotificationLine] = field(
        default_factory=list
    )
    updated_opportunities: list[OpportunityNotificationLine] = field(
        default_factory=list
    )
    review_required: list[OpportunityNotificationLine] = field(
        default_factory=list
    )
    high_priority_ranked: list[OpportunityNotificationLine] = field(
        default_factory=list
    )
    warnings: list[str] = field(default_factory=list)
    assessment_note: str | None = None

    def render_text(self) -> str:
        lines: list[str] = []
        title = "JobHunter automation summary"
        if self.dry_run:
            title += " (dry-run)"
        lines.append(title)
        lines.append(f"Run id: {self.automation_run_id or 'n/a'}")
        lines.append(f"Trigger: {self.trigger_type}")
        if self.assessment_note:
            lines.append(f"Assessment: {self.assessment_note}")
        lines.append("")
        lines.append("Sources:")
        for item in self.source_lines:
            lines.append(f"  - {item}")
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        def _section(header: str, items: list[OpportunityNotificationLine]) -> None:
            if not items:
                return
            lines.append("")
            lines.append(header)
            for entry in items:
                url = entry.source_url or "(no url)"
                band = entry.priority_band or ""
                rank = entry.ranking_status or ""
                elig = entry.eligibility_status or ""
                extra = f" [{elig}"
                if band:
                    extra += f", {band}"
                elif rank:
                    extra += f", {rank}"
                extra += "]"
                lines.append(f"  - {entry.title}{extra}")
                lines.append(f"    {url}")

        _section("New opportunities", self.new_opportunities)
        _section("Materially updated", self.updated_opportunities)
        _section("Review required", self.review_required)
        _section("High-priority ranked", self.high_priority_ranked)
        return "\n".join(lines)


class NotificationSender(Protocol):
    def send(self, summary: AutomationNotificationSummary) -> None: ...

    def send_high_ranking_alert(self, alert: object) -> None: ...


class ConsoleNotificationSender:
    def send(self, summary: AutomationNotificationSummary) -> None:
        print(summary.render_text())

    def send_high_ranking_alert(self, alert: object) -> None:
        from jobhunter.application.automation.high_ranking_alerts import (
            HighRankingOpportunityAlert,
        )

        if isinstance(alert, HighRankingOpportunityAlert):
            print(alert.render_subject())
            print(alert.render_text())


class AutomationNotificationBuilder:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._rankings = OpportunityRankingRepository(session)

    def build(
        self,
        *,
        automation_run: AutomationRun | None,
        trigger_type: str,
        dry_run: bool,
        source_results: list[SourceAdapterResult],
        assessment: AssessmentBatchResult | None,
        ranking_enabled: bool,
        processed_ids: list[str],
        new_ids: list[str],
        updated_ids: list[str],
        warnings: list[str],
    ) -> AutomationNotificationSummary:
        source_lines: list[str] = []
        for result in source_results:
            if result.error_message:
                source_lines.append(
                    f"{result.source_key}: FAILED — {result.error_message}"
                )
            else:
                source_lines.append(
                    f"{result.source_key}: retrieved={result.retrieved} "
                    f"processed={result.processed} failed={result.failed} "
                    f"new={result.created_opportunities}"
                )

        assessment_note: str | None = None
        if assessment is not None:
            if assessment.skipped:
                assessment_note = (
                    assessment.skip_reason or "skipped"
                )
            else:
                assessment_note = (
                    f"assessed={assessment.assessed} reused={assessment.reused} "
                    f"skipped={assessment.skipped_opportunities} "
                    f"failed={assessment.failed}"
                )

        if dry_run:
            new_lines = []
            updated_lines = []
            review_lines = []
            high_priority = []
        else:
            new_lines = self._lines_for_ids(new_ids)
            updated_lines = self._lines_for_ids(updated_ids)
            review_lines = self._review_required_lines(processed_ids)
            high_priority = (
                self._high_priority_lines(processed_ids)
                if ranking_enabled
                else []
            )

        return AutomationNotificationSummary(
            automation_run_id=automation_run.id if automation_run else None,
            trigger_type=trigger_type,
            dry_run=dry_run,
            source_lines=source_lines,
            new_opportunities=new_lines,
            updated_opportunities=updated_lines,
            review_required=review_lines,
            high_priority_ranked=high_priority,
            warnings=warnings,
            assessment_note=assessment_note,
        )

    def _lines_for_ids(self, ids: list[str]) -> list[OpportunityNotificationLine]:
        seen: set[str] = set()
        lines: list[OpportunityNotificationLine] = []
        for opp_id in ids:
            if opp_id in seen:
                continue
            seen.add(opp_id)
            line = self._line_for_opportunity(opp_id)
            if line is not None:
                lines.append(line)
        return lines

    def _line_for_opportunity(
        self, opportunity_id: str
    ) -> OpportunityNotificationLine | None:
        row = self._session.get(OpportunityRow, opportunity_id)
        if row is None:
            return None
        source_url = self._primary_source_url(opportunity_id)
        rankings = self._rankings.list_for_opportunity(opportunity_id)
        ranking = rankings[-1] if rankings else None
        band = (
            ranking.priority_band.value
            if ranking and ranking.priority_band
            else None
        )
        rank_status = ranking.status.value if ranking else None
        return OpportunityNotificationLine(
            opportunity_id=opportunity_id,
            title=row.title,
            source_url=source_url,
            eligibility_status=row.eligibility_status,
            ranking_status=rank_status,
            priority_band=band,
        )

    def _primary_source_url(self, opportunity_id: str) -> str | None:
        stmt = (
            select(OpportunitySourceRow)
            .where(OpportunitySourceRow.opportunity_id == opportunity_id)
            .order_by(OpportunitySourceRow.last_seen_at.desc())
            .limit(1)
        )
        link = self._session.scalars(stmt).first()
        return link.source_url if link else None

    def _review_required_lines(
        self, processed_ids: list[str]
    ) -> list[OpportunityNotificationLine]:
        lines: list[OpportunityNotificationLine] = []
        for opp_id in processed_ids:
            row = self._session.get(OpportunityRow, opp_id)
            if row is None:
                continue
            if row.eligibility_status == EligibilityStatus.REVIEW_REQUIRED.value:
                line = self._line_for_opportunity(opp_id)
                if line:
                    lines.append(line)
        return lines

    def _high_priority_lines(
        self, processed_ids: list[str]
    ) -> list[OpportunityNotificationLine]:
        lines: list[OpportunityNotificationLine] = []
        for opp_id in processed_ids:
            rankings = self._rankings.list_for_opportunity(opp_id)
            ranking = rankings[-1] if rankings else None
            if ranking is None:
                continue
            if ranking.status is not RankingStatus.RANKED:
                continue
            if ranking.priority_band is not PriorityBand.HIGH:
                continue
            line = self._line_for_opportunity(opp_id)
            if line:
                lines.append(line)
        return lines
