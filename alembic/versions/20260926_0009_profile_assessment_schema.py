"""Opportunity profile assessment schema (Phase 8).

Revision ID: 20260926_0009
Revises: 20260926_0008
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0009"
down_revision: Union[str, Sequence[str], None] = "20260926_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_profile_assessments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("search_strategy_revision_id", sa.String(length=36), nullable=False),
        sa.Column("eligibility_decision_id", sa.String(length=36), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("opportunity_content_digest", sa.String(length=64), nullable=False),
        sa.Column("profile_evidence_digest", sa.String(length=64), nullable=False),
        sa.Column("prompt_schema_version", sa.String(length=64), nullable=False),
        sa.Column("model_provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("validation_warnings", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("provider_error", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_profile_assessments_opportunity_id",
        "opportunity_profile_assessments",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_profile_assessments_input_digest",
        "opportunity_profile_assessments",
        ["input_digest"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_profile_assessments_input_digest",
        table_name="opportunity_profile_assessments",
    )
    op.drop_index(
        "ix_opportunity_profile_assessments_opportunity_id",
        table_name="opportunity_profile_assessments",
    )
    op.drop_table("opportunity_profile_assessments")
