"""SQLAlchemy models for search strategy (Phase 4A.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
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


class SearchStrategyRow(Base):
    __tablename__ = "search_strategies"
    __table_args__ = (UniqueConstraint("owner_key", name="uq_search_strategies_owner_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_key: Mapped[str] = mapped_column(String(255), nullable=False)
    current_revision_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "search_strategy_revisions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_search_strategies_current_revision_id",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    revisions: Mapped[list[SearchStrategyRevisionRow]] = relationship(
        back_populates="search_strategy",
        foreign_keys="SearchStrategyRevisionRow.search_strategy_id",
    )


class SearchStrategyRevisionRow(Base):
    __tablename__ = "search_strategy_revisions"
    __table_args__ = (
        UniqueConstraint(
            "search_strategy_id",
            "revision_number",
            name="uq_search_strategy_revisions_strategy_revision_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    search_strategy_id: Mapped[str] = mapped_column(
        ForeignKey("search_strategies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    change_source: Mapped[str] = mapped_column(String(64), nullable=False)
    supersedes_revision_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("search_strategy_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    search_strategy: Mapped[SearchStrategyRow] = relationship(
        back_populates="revisions",
        foreign_keys=[search_strategy_id],
    )
    themes: Mapped[list[SearchThemeRow]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
    )
    criteria: Mapped[list[StrategyCriterionRow]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
    )
    exclusions: Mapped[list[ExclusionCriterionRow]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
    )


class SearchThemeRow(Base):
    __tablename__ = "search_themes"
    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "theme_key",
            name="uq_search_themes_revision_theme_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision_id: Mapped[str] = mapped_column(
        ForeignKey("search_strategy_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    theme_key: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    strength: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text())
    sort_order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    revision: Mapped[SearchStrategyRevisionRow] = relationship(back_populates="themes")


class StrategyCriterionRow(Base):
    __tablename__ = "strategy_criteria"
    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "category",
            "code",
            name="uq_strategy_criteria_revision_category_code",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision_id: Mapped[str] = mapped_column(
        ForeignKey("search_strategy_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    strength: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text())
    sort_order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    revision: Mapped[SearchStrategyRevisionRow] = relationship(
        back_populates="criteria"
    )


class ExclusionCriterionRow(Base):
    __tablename__ = "exclusion_criteria"
    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "exclusion_code",
            name="uq_exclusion_criteria_revision_exclusion_code",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision_id: Mapped[str] = mapped_column(
        ForeignKey("search_strategy_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exclusion_code: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text())

    revision: Mapped[SearchStrategyRevisionRow] = relationship(
        back_populates="exclusions"
    )
