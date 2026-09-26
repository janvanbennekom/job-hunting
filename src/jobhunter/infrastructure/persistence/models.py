"""SQLAlchemy persistence models (not domain entities)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobhunter.infrastructure.persistence.base import Base


class JobSourceRow(Base):
    __tablename__ = "job_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organisation: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    raw_opportunities: Mapped[list[RawOpportunityRow]] = relationship(
        back_populates="source"
    )
    opportunity_links: Mapped[list[OpportunitySourceRow]] = relationship(
        back_populates="source"
    )
    source_scans: Mapped[list[SourceScanRow]] = relationship(
        back_populates="source"
    )


class RawOpportunityRow(Base):
    __tablename__ = "raw_opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("job_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_reference: Mapped[str | None] = mapped_column(String(512))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    raw_title: Mapped[str | None] = mapped_column(String(1024))
    raw_organisation: Mapped[str | None] = mapped_column(String(512))
    raw_location: Mapped[str | None] = mapped_column(String(512))
    raw_deadline: Mapped[str | None] = mapped_column(String(255))
    raw_description: Mapped[str | None] = mapped_column(Text())
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    source: Mapped[JobSourceRow] = relationship(back_populates="raw_opportunities")
    observations: Mapped[list[OpportunityObservationRow]] = relationship(
        back_populates="raw_opportunity"
    )


class OpportunityRow(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    organisation: Mapped[str | None] = mapped_column(String(512))
    location: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text())
    publication_date: Mapped[date | None] = mapped_column(Date())
    deadline: Mapped[date | None] = mapped_column(Date())
    expected_start_date: Mapped[date | None] = mapped_column(Date())
    opportunity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)
    eligibility_status: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_identity_key: Mapped[str | None] = mapped_column(
        String(512), unique=True
    )
    source_status: Mapped[str | None] = mapped_column(String(64))

    source_links: Mapped[list[OpportunitySourceRow]] = relationship(
        back_populates="opportunity"
    )
    observations: Mapped[list[OpportunityObservationRow]] = relationship(
        back_populates="opportunity"
    )
    changes: Mapped[list[OpportunityChangeRow]] = relationship(
        back_populates="opportunity"
    )


class OpportunitySourceRow(Base):
    __tablename__ = "opportunity_sources"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "source_id",
            name="uq_opportunity_sources_opportunity_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("job_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_reference: Mapped[str | None] = mapped_column(String(512))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    original_url: Mapped[str | None] = mapped_column(String(2048))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    opportunity: Mapped[OpportunityRow] = relationship(back_populates="source_links")
    source: Mapped[JobSourceRow] = relationship(back_populates="opportunity_links")


class OpportunityObservationRow(Base):
    __tablename__ = "opportunity_observations"
    __table_args__ = (
        UniqueConstraint(
            "raw_opportunity_id",
            name="uq_opportunity_observations_raw_opportunity_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("raw_opportunities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)

    opportunity: Mapped[OpportunityRow] = relationship(
        back_populates="observations"
    )
    raw_opportunity: Mapped[RawOpportunityRow] = relationship(
        back_populates="observations"
    )
    changes: Mapped[list[OpportunityChangeRow]] = relationship(
        back_populates="observation"
    )


class OpportunityChangeRow(Base):
    __tablename__ = "opportunity_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("opportunity_observations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(Text())
    new_value: Mapped[str | None] = mapped_column(Text())
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    opportunity: Mapped[OpportunityRow] = relationship(back_populates="changes")
    observation: Mapped[OpportunityObservationRow] = relationship(
        back_populates="changes"
    )


class SourceScanRow(Base):
    __tablename__ = "source_scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("job_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    records_retrieved: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0
    )
    records_processed: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0
    )
    records_failed: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0
    )
    error_summary: Mapped[str | None] = mapped_column(Text())

    source: Mapped[JobSourceRow] = relationship(back_populates="source_scans")


class EligibilityDecisionRow(Base):
    __tablename__ = "eligibility_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    search_strategy_revision_id: Mapped[str] = mapped_column(
        ForeignKey("search_strategy_revisions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    rule_results: Mapped[list[EligibilityRuleResultRow]] = relationship(
        back_populates="decision"
    )


class EligibilityRuleResultRow(Base):
    __tablename__ = "eligibility_rule_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("eligibility_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    suggests_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary: Mapped[str | None] = mapped_column(Text())
    evidence: Mapped[str | None] = mapped_column(Text())

    decision: Mapped[EligibilityDecisionRow] = relationship(
        back_populates="rule_results"
    )
