"""add generation credits

Revision ID: f2a7b9d4c681
Revises: e7b2a9c4d613
Create Date: 2026-06-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a7b9d4c681"
down_revision: Union[str, None] = "e7b2a9c4d613"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_order",
        sa.Column(
            "product_code",
            sa.String(length=40),
            server_default="generation_credit",
            nullable=False,
        ),
    )
    op.add_column(
        "payment_order",
        sa.Column("credit_amount", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "payment_order",
        sa.Column("benefit_granted_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "generation_credit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "source_type",
            sa.String(length=30),
            server_default="alipay_sandbox",
            nullable=False,
        ),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("total_credits", sa.Integer(), server_default="1", nullable=False),
        sa.Column("remaining_credits", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_generation_credit_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generation_credit")),
        sa.UniqueConstraint("source_type", "source_id", name="uq_generation_credit_source"),
    )
    op.create_index(op.f("ix_generation_credit_user_id"), "generation_credit", ["user_id"])
    op.create_index(op.f("ix_generation_credit_source_id"), "generation_credit", ["source_id"])
    op.create_index(op.f("ix_generation_credit_remaining_credits"), "generation_credit", ["remaining_credits"])
    op.create_index(op.f("ix_generation_credit_status"), "generation_credit", ["status"])
    op.create_index(op.f("ix_generation_credit_created_at"), "generation_credit", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_generation_credit_created_at"), table_name="generation_credit")
    op.drop_index(op.f("ix_generation_credit_status"), table_name="generation_credit")
    op.drop_index(op.f("ix_generation_credit_remaining_credits"), table_name="generation_credit")
    op.drop_index(op.f("ix_generation_credit_source_id"), table_name="generation_credit")
    op.drop_index(op.f("ix_generation_credit_user_id"), table_name="generation_credit")
    op.drop_table("generation_credit")
    op.drop_column("payment_order", "benefit_granted_at")
    op.drop_column("payment_order", "credit_amount")
    op.drop_column("payment_order", "product_code")
