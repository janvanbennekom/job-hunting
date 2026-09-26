"""Search strategy persistence schema (Phase 4A.2).

Revision ID: 20260926_0005
Revises: 20260926_0004
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260926_0005"
down_revision: Union[str, Sequence[str], None] = "20260926_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_strategies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_key", sa.String(length=255), nullable=False),
        sa.Column("current_revision_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_key", name="uq_search_strategies_owner_key"),
    )
    op.create_table(
        "search_strategy_revisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("search_strategy_id", sa.String(length=36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("change_source", sa.String(length=64), nullable=False),
        sa.Column("supersedes_revision_id", sa.String(length=36), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_strategy_id"],
            ["search_strategies.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["search_strategy_revisions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "search_strategy_id",
            "revision_number",
            name="uq_search_strategy_revisions_strategy_revision_number",
        ),
    )
    op.create_index(
        "ix_search_strategy_revisions_search_strategy_id",
        "search_strategy_revisions",
        ["search_strategy_id"],
    )
    op.create_foreign_key(
        "fk_search_strategies_current_revision_id",
        "search_strategies",
        "search_strategy_revisions",
        ["current_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "search_themes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("revision_id", sa.String(length=36), nullable=False),
        sa.Column("theme_key", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=512), nullable=False),
        sa.Column("strength", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["search_strategy_revisions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "revision_id",
            "theme_key",
            name="uq_search_themes_revision_theme_key",
        ),
    )
    op.create_index("ix_search_themes_revision_id", "search_themes", ["revision_id"])
    op.create_table(
        "strategy_criteria",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("revision_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strength", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["search_strategy_revisions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "revision_id",
            "category",
            "code",
            name="uq_strategy_criteria_revision_category_code",
        ),
    )
    op.create_index(
        "ix_strategy_criteria_revision_id",
        "strategy_criteria",
        ["revision_id"],
    )
    op.create_table(
        "exclusion_criteria",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("revision_id", sa.String(length=36), nullable=False),
        sa.Column("exclusion_code", sa.String(length=64), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["search_strategy_revisions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "revision_id",
            "exclusion_code",
            name="uq_exclusion_criteria_revision_exclusion_code",
        ),
    )
    op.create_index(
        "ix_exclusion_criteria_revision_id",
        "exclusion_criteria",
        ["revision_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_exclusion_criteria_revision_id", table_name="exclusion_criteria")
    op.drop_table("exclusion_criteria")
    op.drop_index("ix_strategy_criteria_revision_id", table_name="strategy_criteria")
    op.drop_table("strategy_criteria")
    op.drop_index("ix_search_themes_revision_id", table_name="search_themes")
    op.drop_table("search_themes")
    op.drop_constraint(
        "fk_search_strategies_current_revision_id",
        "search_strategies",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_search_strategy_revisions_search_strategy_id",
        table_name="search_strategy_revisions",
    )
    op.drop_table("search_strategy_revisions")
    op.drop_table("search_strategies")
