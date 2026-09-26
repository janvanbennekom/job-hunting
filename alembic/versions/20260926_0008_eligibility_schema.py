"""Eligibility decisions schema (Phase 7).

Revision ID: 20260926_0008
Revises: 20260926_0007
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0008"
down_revision: Union[str, Sequence[str], None] = "20260926_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eligibility_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("search_strategy_revision_id", sa.String(length=36), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eligibility_decisions_opportunity_id",
        "eligibility_decisions",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_eligibility_decisions_search_strategy_revision_id",
        "eligibility_decisions",
        ["search_strategy_revision_id"],
    )
    op.create_table(
        "eligibility_rule_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("decision_id", sa.String(length=36), nullable=False),
        sa.Column("rule_kind", sa.String(length=32), nullable=False),
        sa.Column("rule_code", sa.String(length=128), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("suggests_review", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["eligibility_decisions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eligibility_rule_results_decision_id",
        "eligibility_rule_results",
        ["decision_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_eligibility_rule_results_decision_id",
        table_name="eligibility_rule_results",
    )
    op.drop_table("eligibility_rule_results")
    op.drop_index(
        "ix_eligibility_decisions_search_strategy_revision_id",
        table_name="eligibility_decisions",
    )
    op.drop_index(
        "ix_eligibility_decisions_opportunity_id",
        table_name="eligibility_decisions",
    )
    op.drop_table("eligibility_decisions")
