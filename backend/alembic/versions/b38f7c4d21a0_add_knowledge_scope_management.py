"""add knowledge scope management

Revision ID: b38f7c4d21a0
Revises: a912fc4d8301
Create Date: 2026-06-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b38f7c4d21a0"
down_revision: Union[str, None] = "a912fc4d8301"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_file",
        sa.Column("scope", sa.String(length=20), server_default="private", nullable=False),
    )
    op.add_column(
        "knowledge_file",
        sa.Column("file_size", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "knowledge_file",
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "knowledge_file",
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("1"), nullable=False),
    )
    op.create_index(op.f("ix_knowledge_file_scope"), "knowledge_file", ["scope"])
    op.create_index(op.f("ix_knowledge_file_status"), "knowledge_file", ["status"])
    op.create_index(op.f("ix_knowledge_file_is_enabled"), "knowledge_file", ["is_enabled"])


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_file_is_enabled"), table_name="knowledge_file")
    op.drop_index(op.f("ix_knowledge_file_status"), table_name="knowledge_file")
    op.drop_index(op.f("ix_knowledge_file_scope"), table_name="knowledge_file")
    op.drop_column("knowledge_file", "is_enabled")
    op.drop_column("knowledge_file", "chunk_count")
    op.drop_column("knowledge_file", "file_size")
    op.drop_column("knowledge_file", "scope")
