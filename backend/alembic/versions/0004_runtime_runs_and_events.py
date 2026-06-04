"""add runtime runs and timeline events

Revision ID: 0004_runtime_runs_and_events
Revises: 0003_add_users_and_auth
Create Date: 2026-06-03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0004_runtime_runs_and_events"
down_revision = "0003_add_users_and_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="running"),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runtime_runs_project_id"), "runtime_runs", ["project_id"], unique=False)
    op.create_index(op.f("ix_runtime_runs_session_id"), "runtime_runs", ["session_id"], unique=False)
    op.create_index(op.f("ix_runtime_runs_user_id"), "runtime_runs", ["user_id"], unique=False)
    op.create_index(op.f("ix_runtime_runs_agent_id"), "runtime_runs", ["agent_id"], unique=False)
    op.create_index(op.f("ix_runtime_runs_status"), "runtime_runs", ["status"], unique=False)

    op.create_table(
        "runtime_run_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runtime_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runtime_run_events_run_id"), "runtime_run_events", ["run_id"], unique=False)
    op.create_index(op.f("ix_runtime_run_events_stage"), "runtime_run_events", ["stage"], unique=False)
    op.create_index(op.f("ix_runtime_run_events_status"), "runtime_run_events", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_runtime_run_events_status"), table_name="runtime_run_events")
    op.drop_index(op.f("ix_runtime_run_events_stage"), table_name="runtime_run_events")
    op.drop_index(op.f("ix_runtime_run_events_run_id"), table_name="runtime_run_events")
    op.drop_table("runtime_run_events")

    op.drop_index(op.f("ix_runtime_runs_status"), table_name="runtime_runs")
    op.drop_index(op.f("ix_runtime_runs_agent_id"), table_name="runtime_runs")
    op.drop_index(op.f("ix_runtime_runs_user_id"), table_name="runtime_runs")
    op.drop_index(op.f("ix_runtime_runs_session_id"), table_name="runtime_runs")
    op.drop_index(op.f("ix_runtime_runs_project_id"), table_name="runtime_runs")
    op.drop_table("runtime_runs")
