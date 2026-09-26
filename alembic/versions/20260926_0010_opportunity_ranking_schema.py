"""Opportunity ranking schema (Phase 9).

Revision ID: 20260926_0010
Revises: 20260926_0009
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0010"
down_revision: Union[str, Sequence[str], None] = "20260926_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_rankings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("search_strategy_revision_id", sa.String(length=36), nullable=False),
        sa.Column("eligibility_decision_id", sa.String(length=36), nullable=True),
        sa.Column("profile_assessment_id", sa.String(length=36), nullable=True),
        sa.Column("ranked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority_band", sa.String(length=16), nullable=True),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("ranking_method_version", sa.String(length=64), nullable=False),
        sa.Column("ranking_config_hash", sa.String(length=64), nullable=False),
        sa.Column("internal_sort_score", sa.Integer(), nullable=True),
        sa.Column("factors", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("exclusion_reason", sa.String(length=64), nullable=True),
        sa.Column("unranked_reason", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["search_strategy_revision_id"],
            ["search_strategy_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["eligibility_decision_id"],
            ["eligibility_decisions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["profile_assessment_id"],
            ["opportunity_profile_assessments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_rankings_opportunity_id",
        "opportunity_rankings",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_rankings_input_digest",
        "opportunity_rankings",
        ["input_digest"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_rankings_input_digest",
        table_name="opportunity_rankings",
    )
    op.drop_index(
        "ix_opportunity_rankings_opportunity_id",
        table_name="opportunity_rankings",
    )
    op.drop_table("opportunity_rankings")
