"""Add AI usage table.

Revision ID: 20261105_0001
Revises: 20261101_0001
Create Date: 2026-11-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261105_0001"
down_revision: Union[str, None] = "20261101_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_usage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="success", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_ai_usage_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_ai_usage"),
    )
    op.create_index("ix_ai_usage_user_created", "ai_usage", ["user_id", sa.text("created_at DESC")])
    op.create_index("ix_ai_usage_task_created", "ai_usage", ["task", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_ai_usage_task_created", table_name="ai_usage")
    op.drop_index("ix_ai_usage_user_created", table_name="ai_usage")
    op.drop_table("ai_usage")
