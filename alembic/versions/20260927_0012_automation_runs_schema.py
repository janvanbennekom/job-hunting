"""Automation run audit persistence (Phase 13).

Revision ID: 20260927_0012
Revises: 20260926_0011
Create Date: 2026-09-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260927_0012"
down_revision: Union[str, Sequence[str], None] = "20260926_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("config_snapshot", JSONB(), nullable=False, server_default="{}"),
        sa.Column("source_scan_ids", JSONB(), nullable=False, server_default="[]"),
        sa.Column("records_retrieved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_succeeded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_runs_started_at",
        "automation_runs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_automation_runs_started_at", table_name="automation_runs")
    op.drop_table("automation_runs")
