"""add quota and model usage

Revision ID: a912fc4d8301
Revises: f6c31a72b904
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a912fc4d8301"
down_revision: Union[str, None] = "f6c31a72b904"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_generation_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("successful_generations", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_daily_generation_usage_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_daily_generation_usage")),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_daily_generation_usage_user_date"),
    )
    op.create_index(op.f("ix_daily_generation_usage_user_id"), "daily_generation_usage", ["user_id"])
    op.create_index(op.f("ix_daily_generation_usage_usage_date"), "daily_generation_usage", ["usage_date"])

    op.create_table(
        "model_call_usage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("success", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_model_call_usage_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_call_usage")),
    )
    op.create_index(op.f("ix_model_call_usage_user_id"), "model_call_usage", ["user_id"])
    op.create_index(op.f("ix_model_call_usage_success"), "model_call_usage", ["success"])
    op.create_index(op.f("ix_model_call_usage_request_id"), "model_call_usage", ["request_id"])
    op.create_index(op.f("ix_model_call_usage_created_at"), "model_call_usage", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_model_call_usage_created_at"), table_name="model_call_usage")
    op.drop_index(op.f("ix_model_call_usage_request_id"), table_name="model_call_usage")
    op.drop_index(op.f("ix_model_call_usage_success"), table_name="model_call_usage")
    op.drop_index(op.f("ix_model_call_usage_user_id"), table_name="model_call_usage")
    op.drop_table("model_call_usage")
    op.drop_index(op.f("ix_daily_generation_usage_usage_date"), table_name="daily_generation_usage")
    op.drop_index(op.f("ix_daily_generation_usage_user_id"), table_name="daily_generation_usage")
    op.drop_table("daily_generation_usage")
