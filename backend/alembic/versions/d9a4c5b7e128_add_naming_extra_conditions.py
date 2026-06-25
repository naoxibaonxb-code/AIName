"""add naming extra conditions

Revision ID: d9a4c5b7e128
Revises: c2f9a6d4e317
Create Date: 2026-06-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9a4c5b7e128"
down_revision: Union[str, None] = "c2f9a6d4e317"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "naming_session",
        sa.Column("extra_conditions", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("naming_session", "extra_conditions")
