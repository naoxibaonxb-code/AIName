"""add payment orders

Revision ID: e7b2a9c4d613
Revises: d9a4c5b7e128
Create Date: 2026-06-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7b2a9c4d613"
down_revision: Union[str, None] = "d9a4c5b7e128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_order",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("out_trade_no", sa.String(length=64), nullable=False),
        sa.Column("trade_no", sa.String(length=64), nullable=True),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("buyer_id", sa.String(length=64), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("raw_notify", sa.String(length=4000), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_payment_order_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_order")),
    )
    op.create_index(op.f("ix_payment_order_user_id"), "payment_order", ["user_id"])
    op.create_index(op.f("ix_payment_order_out_trade_no"), "payment_order", ["out_trade_no"], unique=True)
    op.create_index(op.f("ix_payment_order_trade_no"), "payment_order", ["trade_no"])
    op.create_index(op.f("ix_payment_order_status"), "payment_order", ["status"])
    op.create_index(op.f("ix_payment_order_created_at"), "payment_order", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_order_created_at"), table_name="payment_order")
    op.drop_index(op.f("ix_payment_order_status"), table_name="payment_order")
    op.drop_index(op.f("ix_payment_order_trade_no"), table_name="payment_order")
    op.drop_index(op.f("ix_payment_order_out_trade_no"), table_name="payment_order")
    op.drop_index(op.f("ix_payment_order_user_id"), table_name="payment_order")
    op.drop_table("payment_order")
