"""add user center data

Revision ID: c7a91e42d830
Revises: 8d51f14a1b02
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7a91e42d830"
down_revision: Union[str, None] = "8d51f14a1b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "user",
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("user", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_table(
        "login_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("login_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_login_record_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_record")),
    )
    op.create_index(op.f("ix_login_record_user_id"), "login_record", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_login_record_user_id"), table_name="login_record")
    op.drop_table("login_record")
    op.drop_column("user", "deleted_at")
    op.drop_column("user", "usage_count")
    op.drop_column("user", "created_at")
