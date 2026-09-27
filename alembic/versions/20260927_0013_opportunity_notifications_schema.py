"""Opportunity notification audit (Phase 13 alerts).

Revision ID: 20260927_0013
Revises: 20260927_0012
Create Date: 2026-09-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_0013"
down_revision: Union[str, Sequence[str], None] = "20260927_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("ranking_id", sa.String(length=36), nullable=False),
        sa.Column("notification_type", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("notification_key", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ranking_id"],
            ["opportunity_rankings.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_key", name="uq_opportunity_notifications_key"),
    )
    op.create_index(
        "ix_opportunity_notifications_opportunity_id",
        "opportunity_notifications",
        ["opportunity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_notifications_opportunity_id",
        table_name="opportunity_notifications",
    )
    op.drop_table("opportunity_notifications")
