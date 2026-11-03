"""Create the multi-user application schema.

Revision ID: 20261101_0001
Revises:
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261101_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("id", "email", name="uq_users_id_email"),
    )
    op.create_index(
        "uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True
    )

    op.create_table(
        "sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_sessions_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_user_expires", "sessions", ["user_id", "expires_at"])

    op.create_table(
        "gmail_credentials",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_email", sa.String(length=254), nullable=False),
        sa.Column("encrypted_app_password", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_gmail_credentials_user_id_users"),
        sa.PrimaryKeyConstraint("user_id", name="pk_gmail_credentials"),
    )

    op.create_table(
        "sender_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=120), server_default="", nullable=False),
        sa.Column("contact_email", sa.String(length=254), server_default="", nullable=False),
        sa.Column("phone", sa.String(length=40), server_default="", nullable=False),
        sa.Column("location", sa.String(length=160), server_default="", nullable=False),
        sa.Column("portfolio_url", sa.String(length=500), server_default="", nullable=False),
        sa.Column("linkedin_url", sa.String(length=500), server_default="", nullable=False),
        sa.Column("github_url", sa.String(length=500), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_sender_profiles_user_id_users"),
        sa.PrimaryKeyConstraint("user_id", name="pk_sender_profiles"),
    )

    op.create_table(
        "resume_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("title_keywords", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("description_keywords", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("excluded_roles", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("excluded_seniority_keywords", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("seniority_limit", sa.String(length=40), server_default="any", nullable=False),
        sa.Column("remote_preference", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_resume_profiles_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_resume_profiles"),
        sa.UniqueConstraint("id", "user_id", name="uq_resume_profiles_id_user"),
    )
    op.create_index("ix_resume_profiles_user_created", "resume_profiles", ["user_id", "created_at"])

    op.create_table(
        "resume_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("size_bytes > 0", name="ck_resume_files_resume_file_size_positive"),
        sa.ForeignKeyConstraint(
            ["profile_id", "user_id"],
            ["resume_profiles.id", "resume_profiles.user_id"],
            ondelete="CASCADE",
            name="fk_resume_files_profile_user",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resume_files"),
        sa.UniqueConstraint("object_key", name="uq_resume_files_object_key"),
    )
    op.create_index("ix_resume_files_user_profile", "resume_files", ["user_id", "profile_id"])

    op.create_table(
        "jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_job_id", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("company", sa.String(length=300), server_default="", nullable=False),
        sa.Column("location", sa.String(length=300), server_default="", nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("company_email", sa.String(length=254), server_default="", nullable=False),
        sa.Column("posted_at", sa.Date(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.UniqueConstraint("source", "source_job_id", name="uq_jobs_source_job"),
    )
    op.create_index("ix_jobs_posted_at", "jobs", [sa.text("posted_at DESC")])
    op.create_index("ix_jobs_discovered_at", "jobs", [sa.text("discovered_at DESC")])
    op.create_index("ix_jobs_title", "jobs", ["title"])

    op.create_table(
        "runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="queued", nullable=False),
        sa.Column("stage", sa.String(length=80), server_default="queued", nullable=False),
        sa.Column("task_id", sa.String(length=200), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("progress", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("checkpoint", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'cancelling', 'completed', 'cancelled', 'failed')",
            name="ck_runs_run_status_valid",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_runs_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_runs"),
        sa.UniqueConstraint("id", "user_id", name="uq_runs_id_user"),
    )
    op.create_index("ix_runs_user_created", "runs", ["user_id", sa.text("created_at DESC")])
    op.create_index(
        "uq_runs_one_active_per_user",
        "runs",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running', 'cancelling')"),
    )

    op.create_table(
        "applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("profile_used", sa.String(length=120), server_default="", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="discovered", nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skip_reason", sa.String(length=80), nullable=True),
        sa.Column("email_subject", sa.String(length=500), server_default="", nullable=False),
        sa.Column("email_body", sa.Text(), server_default="", nullable=False),
        sa.Column("cover_letter_path", sa.String(length=1024), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("score >= 0", name="ck_applications_application_score_nonnegative"),
        sa.CheckConstraint(
            "status IN ('discovered', 'awaiting_review', 'approved', 'sending', 'applied', 'skipped', 'failed')",
            name="ck_applications_application_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_applications_job_id_jobs"
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "user_id"],
            ["runs.id", "runs.user_id"],
            ondelete="SET NULL (run_id)",
            name="fk_applications_run_user",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_applications_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_applications"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_applications_user_idempotency"),
    )
    op.create_index(
        "ix_applications_user_status_created",
        "applications",
        ["user_id", "status", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_applications_user_score",
        "applications",
        ["user_id", sa.text("score DESC")],
    )
    op.create_index("ix_applications_user_skip_reason", "applications", ["user_id", "skip_reason"])
    op.create_index("ix_applications_user_profile", "applications", ["user_id", "profile_used"])
    op.create_index(
        "ix_applications_user_sent_at",
        "applications",
        ["user_id", sa.text("sent_at DESC")],
    )

    op.create_table(
        "run_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.String(length=12), server_default="info", nullable=False),
        sa.Column("stage", sa.String(length=80), server_default="", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "level IN ('debug', 'info', 'warning', 'error')",
            name="ck_run_logs_run_log_level_valid",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "user_id"],
            ["runs.id", "runs.user_id"],
            ondelete="CASCADE",
            name="fk_run_logs_run_user",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_run_logs"),
    )
    op.create_index("ix_run_logs_run_created", "run_logs", ["run_id", "created_at"])
    op.create_index("ix_run_logs_user_created", "run_logs", ["user_id", "created_at"])

    op.create_table(
        "settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("onboarding_complete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("dry_run", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("daily_application_cap", sa.Integer(), server_default="5", nullable=False),
        sa.Column("minimum_fit_score", sa.Integer(), server_default="4", nullable=False),
        sa.Column("schedule_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("schedule_timezone", sa.String(length=80), server_default="UTC", nullable=False),
        sa.Column("schedule_days", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("schedule_time", sa.String(length=5), server_default="09:00", nullable=False),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "daily_application_cap BETWEEN 0 AND 100",
            name="ck_settings_daily_cap_valid",
        ),
        sa.CheckConstraint(
            "minimum_fit_score BETWEEN 0 AND 100",
            name="ck_settings_minimum_fit_score_valid",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_settings_user_id_users"
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_settings"),
    )

    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_audit_log_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )
    op.create_index("ix_audit_log_user_created", "audit_log", ["user_id", sa.text("created_at DESC")])
    op.create_index("ix_audit_log_action_created", "audit_log", ["action", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("settings")
    op.drop_table("run_logs")
    op.drop_table("applications")
    op.drop_table("runs")
    op.drop_table("jobs")
    op.drop_table("resume_files")
    op.drop_table("resume_profiles")
    op.drop_table("sender_profiles")
    op.drop_table("gmail_credentials")
    op.drop_table("sessions")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")
