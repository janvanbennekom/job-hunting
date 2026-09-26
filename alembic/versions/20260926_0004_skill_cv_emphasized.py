"""Add cv_emphasized to skills (Phase 3C.3B).

Revision ID: 20260926_0004
Revises: 20260926_0003
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0004"
down_revision: Union[str, Sequence[str], None] = "20260926_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "skills",
        sa.Column(
            "cv_emphasized",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("skills", "cv_emphasized", server_default=None)


def downgrade() -> None:
    op.drop_column("skills", "cv_emphasized")
