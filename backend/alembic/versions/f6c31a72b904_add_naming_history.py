"""add naming history and favorites

Revision ID: f6c31a72b904
Revises: e4b81f09a621
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6c31a72b904"
down_revision: Union[str, None] = "e4b81f09a621"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "naming_session",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("surname", sa.String(length=20), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("name_length", sa.String(length=10), nullable=False),
        sa.Column("other", sa.Text(), nullable=False),
        sa.Column("exclude", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_naming_session_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_naming_session")),
    )
    op.create_index(op.f("ix_naming_session_user_id"), "naming_session", ["user_id"])
    op.create_index(op.f("ix_naming_session_category"), "naming_session", ["category"])
    op.create_index(op.f("ix_naming_session_created_at"), "naming_session", ["created_at"])
    op.create_index(op.f("ix_naming_session_expires_at"), "naming_session", ["expires_at"])

    op.create_table(
        "naming_round",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("names", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["naming_session.id"], name=op.f("fk_naming_round_session_id_naming_session"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_naming_round")),
        sa.UniqueConstraint("session_id", "round_number", name="uq_naming_round_session_number"),
    )
    op.create_index(op.f("ix_naming_round_session_id"), "naming_round", ["session_id"])

    op.create_table(
        "favorite_name",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_session_id", sa.String(length=36), nullable=True),
        sa.Column("source_round_number", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_favorite_name_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_favorite_name")),
    )
    op.create_index(op.f("ix_favorite_name_user_id"), "favorite_name", ["user_id"])
    op.create_index(op.f("ix_favorite_name_name"), "favorite_name", ["name"])


def downgrade() -> None:
    op.drop_index(op.f("ix_favorite_name_name"), table_name="favorite_name")
    op.drop_index(op.f("ix_favorite_name_user_id"), table_name="favorite_name")
    op.drop_table("favorite_name")
    op.drop_index(op.f("ix_naming_round_session_id"), table_name="naming_round")
    op.drop_table("naming_round")
    op.drop_index(op.f("ix_naming_session_expires_at"), table_name="naming_session")
    op.drop_index(op.f("ix_naming_session_created_at"), table_name="naming_session")
    op.drop_index(op.f("ix_naming_session_category"), table_name="naming_session")
    op.drop_index(op.f("ix_naming_session_user_id"), table_name="naming_session")
    op.drop_table("naming_session")
