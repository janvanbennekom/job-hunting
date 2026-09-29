"""Add OpenAI token usage columns to opportunity_profile_assessments.

Revision ID: 20260929_0015
Revises: 20260928_0014
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260929_0015"
down_revision: Union[str, Sequence[str], None] = "20260928_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opportunity_profile_assessments",
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "opportunity_profile_assessments",
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "opportunity_profile_assessments",
        sa.Column("total_tokens", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("opportunity_profile_assessments", "total_tokens")
    op.drop_column("opportunity_profile_assessments", "completion_tokens")
    op.drop_column("opportunity_profile_assessments", "prompt_tokens")
