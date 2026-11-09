"""Add structured profile, answer bank, and application activity tables.

Revision ID: 20261109_0001
Revises: 20261105_0001
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261109_0001"
down_revision: Union[str, None] = "20261105_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), server_default="", nullable=False),
        sa.Column("role", sa.String(length=120), server_default="", nullable=False),
        sa.Column("headline", sa.String(length=200), server_default="", nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("target_roles", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("include_keywords", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("exclude_keywords", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("preferred_locations", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("seniority_level", sa.String(length=40), server_default="unspecified", nullable=False),
        sa.Column("years_experience", sa.Integer(), server_default="0", nullable=False),
        sa.Column("domains", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("remote_preference", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("daily_apply_cap", sa.Integer(), server_default="5", nullable=False),
        sa.Column("min_match_score", sa.Integer(), server_default="4", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_bot_profiles_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_bot_profiles"),
        sa.UniqueConstraint("id", "user_id", name="uq_bot_profiles_id_user"),
        sa.CheckConstraint("daily_apply_cap >= 1", name="bot_profiles_daily_apply_cap_positive"),
        sa.CheckConstraint("years_experience >= 0", name="bot_profiles_years_experience_nonnegative"),
    )
    op.create_index("ix_bot_profiles_user_created", "bot_profiles", ["user_id", "created_at"])

    op.create_table(
        "education",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school", sa.String(length=200), server_default="", nullable=False),
        sa.Column("degree", sa.String(length=150), server_default="", nullable=False),
        sa.Column("field_of_study", sa.String(length=150), server_default="", nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_education_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_education"),
    )
    op.create_index("ix_education_user_created", "education", ["user_id", "created_at"])

    op.create_table(
        "work_experience",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company", sa.String(length=200), server_default="", nullable=False),
        sa.Column("role", sa.String(length=150), server_default="", nullable=False),
        sa.Column("start_date", sa.String(length=20), server_default="", nullable=False),
        sa.Column("end_date", sa.String(length=20), server_default="", nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("achievements", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_work_experience_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_work_experience"),
    )
    op.create_index("ix_work_experience_user_created", "work_experience", ["user_id", "created_at"])

    op.create_table(
        "answer_bank",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_answer_bank_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_answer_bank"),
    )
    op.create_index("ix_answer_bank_user_created", "answer_bank", ["user_id", "created_at"])

    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=50), server_default="note", nullable=False),
        sa.Column("details", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_application_events_user_id_users"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE", name="fk_application_events_application_id_applications"),
        sa.PrimaryKeyConstraint("id", name="pk_application_events"),
    )
    op.create_index("ix_application_events_user_created", "application_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_application_events_user_created", table_name="application_events")
    op.drop_table("application_events")
    op.drop_index("ix_answer_bank_user_created", table_name="answer_bank")
    op.drop_table("answer_bank")
    op.drop_index("ix_work_experience_user_created", table_name="work_experience")
    op.drop_table("work_experience")
    op.drop_index("ix_education_user_created", table_name="education")
    op.drop_table("education")
    op.drop_index("ix_bot_profiles_user_created", table_name="bot_profiles")
    op.drop_table("bot_profiles")
