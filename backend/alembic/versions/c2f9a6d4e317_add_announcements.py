"""add announcements

Revision ID: c2f9a6d4e317
Revises: b38f7c4d21a0
Create Date: 2026-06-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2f9a6d4e317"
down_revision: Union[str, None] = "b38f7c4d21a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "announcement",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=20), server_default="info", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_announcement")),
    )
    op.create_index(op.f("ix_announcement_is_active"), "announcement", ["is_active"])
    op.create_index(op.f("ix_announcement_created_at"), "announcement", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_announcement_created_at"), table_name="announcement")
    op.drop_index(op.f("ix_announcement_is_active"), table_name="announcement")
    op.drop_table("announcement")
