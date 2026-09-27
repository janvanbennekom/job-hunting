"""Immediate HIGH-band opportunity alerts (Phase 13 extension)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.application.automation.notification import NotificationSender
from jobhunter.application.ranking.service import RankingOutcome
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity_notification import (
    OpportunityNotification,
    high_ranking_notification_key,
)
from jobhunter.domain.opportunity_notification_enums import (
    OpportunityNotificationChannel,
    OpportunityNotificationStatus,
    OpportunityNotificationType,
)
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.infrastructure.config import Settings
from jobhunter.infrastructure.web_urls import build_opportunity_dashboard_url
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.models import OpportunitySourceRow
from jobhunter.infrastructure.persistence.opportunity_notification_repository import (
    OpportunityNotificationRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository


@dataclass(frozen=True, slots=True)
class HighRankingOpportunityAlert:
    opportunity_id: str
    title: str
    source_name: str | None
    organisation: str | None
    location: str | None
    deadline: str | None
    priority_band: str
    ranking_factors: list[str]
    strengths: list[str]
    gaps: list[str]
    uncertainties: list[str]
    source_url: str | None
    dashboard_url: str | None

    def render_subject(self) -> str:
        return f"JobHunter HIGH opportunity: {self.title[:120]}"

    def render_text(self) -> str:
        lines = [
            "JobHunter — HIGH priority opportunity",
            "",
            f"Title: {self.title}",
        ]
        if self.source_name:
            lines.append(f"Source: {self.source_name}")
        if self.organisation:
            lines.append(f"Organisation: {self.organisation}")
        if self.location:
            lines.append(f"Location: {self.location}")
        if self.deadline:
            lines.append(f"Deadline: {self.deadline}")
        lines.append(f"Ranking band: {self.priority_band}")
        if self.ranking_factors:
            lines.append("")
            lines.append("Ranking factors:")
            for item in self.ranking_factors[:8]:
                lines.append(f"  - {item}")
        if self.strengths:
            lines.append("")
            lines.append("Key alignments:")
            for item in self.strengths[:5]:
                lines.append(f"  - {item}")
        if self.gaps:
            lines.append("")
            lines.append("Important gaps:")
            for item in self.gaps[:5]:
                lines.append(f"  - {item}")
        if self.uncertainties:
            lines.append("")
            lines.append("Uncertainties:")
            for item in self.uncertainties[:5]:
                lines.append(f"  - {item}")
        lines.append("")
        if self.source_url:
            lines.append(f"Source: {self.source_url}")
        if self.dashboard_url:
            lines.append(f"JobHunter: {self.dashboard_url}")
        return "\n".join(lines)


@dataclass(slots=True)
class HighRankingAlertRunResult:
    attempted: int = 0
    sent: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def ranking_eligible_for_high_alert(
    *,
    lifecycle_status: LifecycleStatus,
    eligibility_status: EligibilityStatus,
    ranking_status: RankingStatus,
    priority_band: PriorityBand | None,
    assessment_provider: str | None,
) -> bool:
    if lifecycle_status in (LifecycleStatus.CLOSED, LifecycleStatus.EXPIRED):
        return False
    if eligibility_status is EligibilityStatus.INELIGIBLE:
        return False
    if ranking_status is not RankingStatus.RANKED:
        return False
    if priority_band is not PriorityBand.HIGH:
        return False
    if not assessment_provider or assessment_provider == "fake":
        return False
    return True


class HighRankingAlertService:
    """Evaluate and deliver HIGH ranking alerts for newly produced rankings."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
    ) -> None:
        self._session = session
        self._settings = settings
        self._opportunities = OpportunityRepository(session)
        self._assessments = OpportunityProfileAssessmentRepository(session)
        self._notifications = OpportunityNotificationRepository(session)

    def process_ranking_outcomes(
        self,
        outcomes: list[RankingOutcome],
        *,
        sender: NotificationSender,
    ) -> HighRankingAlertRunResult:
        result = HighRankingAlertRunResult()
        channel = (
            OpportunityNotificationChannel.SMTP
            if self._settings.smtp_configured()
            else OpportunityNotificationChannel.CONSOLE
        )
        for outcome in outcomes:
            if outcome.reused:
                result.skipped += 1
                continue
            try:
                self._process_one(outcome, sender=sender, channel=channel, result=result)
            except Exception as exc:  # noqa: BLE001
                result.failed += 1
                result.errors.append(f"{outcome.ranking.opportunity_id}: {exc}")
        return result

    def _process_one(
        self,
        outcome: RankingOutcome,
        *,
        sender: NotificationSender,
        channel: OpportunityNotificationChannel,
        result: HighRankingAlertRunResult,
    ) -> None:
        ranking = outcome.ranking
        opportunity = self._opportunities.get_by_id(ranking.opportunity_id)
        if opportunity is None:
            return

        assessment = None
        if ranking.profile_assessment_id:
            assessment = self._assessments.get_by_id(ranking.profile_assessment_id)

        provider = assessment.model_provider if assessment else None
        if not ranking_eligible_for_high_alert(
            lifecycle_status=opportunity.lifecycle_status,
            eligibility_status=opportunity.eligibility_status,
            ranking_status=ranking.status,
            priority_band=ranking.priority_band,
            assessment_provider=provider,
        ):
            result.skipped += 1
            return

        notification_key = high_ranking_notification_key(ranking.id)
        if self._notifications.has_successful_delivery(notification_key):
            result.skipped += 1
            return

        alert = self._build_alert(opportunity, ranking, assessment)
        result.attempted += 1
        attempted_at = datetime.now(timezone.utc)
        record = self._notifications.get_by_key(notification_key)
        if record is None:
            record = OpportunityNotification(
                opportunity_id=ranking.opportunity_id,
                ranking_id=ranking.id,
                notification_type=OpportunityNotificationType.HIGH_RANKING,
                channel=channel,
                status=OpportunityNotificationStatus.FAILED,
                attempted_at=attempted_at,
                notification_key=notification_key,
            )
        else:
            record.attempted_at = attempted_at
            record.channel = channel

        try:
            sender.send_high_ranking_alert(alert)
            record.status = OpportunityNotificationStatus.SENT
            record.sent_at = datetime.now(timezone.utc)
            record.error_summary = None
            self._notifications.save(record)
            result.sent += 1
        except Exception as exc:  # noqa: BLE001
            record.status = OpportunityNotificationStatus.FAILED
            record.sent_at = None
            record.error_summary = str(exc)[:2000]
            self._notifications.save(record)
            result.failed += 1
            result.errors.append(
                f"{ranking.opportunity_id}: {record.error_summary}"
            )

    def _build_alert(self, opportunity, ranking, assessment) -> HighRankingOpportunityAlert:
        source_name, source_url = self._primary_source(ranking.opportunity_id)
        factors = [
            f"{f.code}: {f.summary}" for f in ranking.factors[:8]
        ]
        strengths: list[str] = []
        gaps: list[str] = []
        uncertainties: list[str] = []
        if assessment and assessment.result:
            raw = assessment.result
            for key in ("strengths", "gaps", "uncertainties"):
                items = raw.get(key) or []
                if isinstance(items, list):
                    target = strengths if key == "strengths" else gaps if key == "gaps" else uncertainties
                    for item in items[:5]:
                        if isinstance(item, str):
                            target.append(item[:500])
                        elif isinstance(item, dict):
                            aspect = item.get("aspect") or item.get("summary") or ""
                            details = item.get("details") or ""
                            text = f"{aspect}: {details}".strip(": ")
                            if text:
                                target.append(text[:500])
        deadline = (
            opportunity.deadline.isoformat() if opportunity.deadline else None
        )
        dashboard_url = build_opportunity_dashboard_url(
            self._settings.web_base_url,
            opportunity.id,
        )
        return HighRankingOpportunityAlert(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            source_name=source_name,
            organisation=opportunity.organisation,
            location=opportunity.location,
            deadline=deadline,
            priority_band=ranking.priority_band.value if ranking.priority_band else "HIGH",
            ranking_factors=factors,
            strengths=strengths,
            gaps=gaps,
            uncertainties=uncertainties,
            source_url=source_url,
            dashboard_url=dashboard_url,
        )

    def _primary_source(self, opportunity_id: str) -> tuple[str | None, str | None]:
        stmt = (
            select(OpportunitySourceRow)
            .where(OpportunitySourceRow.opportunity_id == opportunity_id)
            .order_by(OpportunitySourceRow.last_seen_at.desc())
            .limit(1)
        )
        link = self._session.scalars(stmt).first()
        if link is None:
            return None, None
        source_name = link.source_id
        return source_name, link.source_url
