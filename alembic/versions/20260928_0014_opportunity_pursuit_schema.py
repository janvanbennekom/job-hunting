"""Opportunity pursuit / application tracking (Phase 14).

Revision ID: 20260928_0014
Revises: 20260927_0013
Create Date: 2026-09-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260928_0014"
down_revision: Union[str, Sequence[str], None] = "20260927_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_pursuits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submission_deadline", sa.Date(), nullable=True),
        sa.Column("submission_url", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_action_date", sa.Date(), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_organisation", sa.String(length=255), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("reference_identifier", sa.String(length=255), nullable=True),
        sa.Column("operational_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "opportunity_id", name="uq_opportunity_pursuits_opportunity"
        ),
    )
    op.create_index(
        "ix_opportunity_pursuits_opportunity_id",
        "opportunity_pursuits",
        ["opportunity_id"],
    )
    op.create_table(
        "opportunity_pursuit_status_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pursuit_id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pursuit_id"],
            ["opportunity_pursuits.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_pursuit_status_events_pursuit_recorded",
        "opportunity_pursuit_status_events",
        ["pursuit_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_pursuit_status_events_pursuit_recorded",
        table_name="opportunity_pursuit_status_events",
    )
    op.drop_table("opportunity_pursuit_status_events")
    op.drop_index(
        "ix_opportunity_pursuits_opportunity_id",
        table_name="opportunity_pursuits",
    )
    op.drop_table("opportunity_pursuits")
