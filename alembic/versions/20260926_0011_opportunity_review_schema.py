"""Opportunity human review records (Phase 10).

Revision ID: 20260926_0011
Revises: 20260926_0010
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0011"
down_revision: Union[str, Sequence[str], None] = "20260926_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_review_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("search_strategy_revision_id", sa.String(length=36), nullable=True),
        sa.Column("profile_assessment_id", sa.String(length=36), nullable=True),
        sa.Column("ranking_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["search_strategy_revision_id"],
            ["search_strategy_revisions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["profile_assessment_id"],
            ["opportunity_profile_assessments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ranking_id"],
            ["opportunity_rankings.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_review_records_opportunity_recorded",
        "opportunity_review_records",
        ["opportunity_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_review_records_opportunity_recorded",
        table_name="opportunity_review_records",
    )
    op.drop_table("opportunity_review_records")
