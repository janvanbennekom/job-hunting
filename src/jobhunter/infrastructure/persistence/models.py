"""SQLAlchemy persistence models (not domain entities)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


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

    source_links: Mapped[list[OpportunitySourceRow]] = relationship(
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
