"""add knowledge files

Revision ID: e4b81f09a621
Revises: c7a91e42d830
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4b81f09a621"
down_revision: Union[str, None] = "c7a91e42d830"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_file",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_knowledge_file_user_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_file")),
        sa.UniqueConstraint("stored_name", name=op.f("uq_knowledge_file_stored_name")),
    )
    op.create_index(
        op.f("ix_knowledge_file_user_id"), "knowledge_file", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_file_user_id"), table_name="knowledge_file")
    op.drop_table("knowledge_file")
