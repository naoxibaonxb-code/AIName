"""add user role and status

Revision ID: 8d51f14a1b02
Revises: 23fc691c9945
Create Date: 2026-06-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8d51f14a1b02"
down_revision: Union[str, None] = "23fc691c9945"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
    )
    op.add_column(
        "user",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user", "is_active")
    op.drop_column("user", "role")
