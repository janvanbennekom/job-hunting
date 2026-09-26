"""Opportunity processing schema (Phase 5).

Revision ID: 20260926_0006
Revises: 20260926_0005
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0006"
down_revision: Union[str, Sequence[str], None] = "20260926_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("canonical_identity_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("source_status", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_opportunities_canonical_identity_key",
        "opportunities",
        ["canonical_identity_key"],
        unique=True,
    )
    op.create_table(
        "opportunity_observations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("raw_opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["raw_opportunity_id"],
            ["raw_opportunities.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "raw_opportunity_id",
            name="uq_opportunity_observations_raw_opportunity_id",
        ),
    )
    op.create_index(
        "ix_opportunity_observations_opportunity_id",
        "opportunity_observations",
        ["opportunity_id"],
    )
    op.create_table(
        "opportunity_changes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("observation_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["opportunity_observations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_changes_opportunity_id",
        "opportunity_changes",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_changes_observation_id",
        "opportunity_changes",
        ["observation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_changes_observation_id", table_name="opportunity_changes"
    )
    op.drop_index(
        "ix_opportunity_changes_opportunity_id", table_name="opportunity_changes"
    )
    op.drop_table("opportunity_changes")
    op.drop_index(
        "ix_opportunity_observations_opportunity_id",
        table_name="opportunity_observations",
    )
    op.drop_table("opportunity_observations")
    op.drop_index(
        "uq_opportunities_canonical_identity_key", table_name="opportunities"
    )
    op.drop_column("opportunities", "source_status")
    op.drop_column("opportunities", "canonical_identity_key")
