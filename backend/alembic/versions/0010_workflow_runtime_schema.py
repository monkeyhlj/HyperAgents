"""add workflow runtime schema

Revision ID: 0010_workflow_runtime_schema
Revises: 0009_chat_messages_agent_id
Create Date: 2026-07-30 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010_workflow_runtime_schema"
down_revision = "0009_chat_messages_agent_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("triggered_by", sa.String(length=120), nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_runs_workflow_id"), "workflow_runs", ["workflow_id"], unique=False)
    op.create_index(op.f("ix_workflow_runs_project_id"), "workflow_runs", ["project_id"], unique=False)
    op.create_index(op.f("ix_workflow_runs_triggered_by"), "workflow_runs", ["triggered_by"], unique=False)
    op.create_index(op.f("ix_workflow_runs_status"), "workflow_runs", ["status"], unique=False)
    op.create_index("ix_workflow_runs_workflow_created", "workflow_runs", ["workflow_id", "created_at"], unique=False)

    op.create_table(
        "workflow_step_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("step_id", sa.String(length=120), nullable=False),
        sa.Column("step_name", sa.String(length=160), nullable=True),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["resources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_step_executions_workflow_run_id"), "workflow_step_executions", ["workflow_run_id"], unique=False)
    op.create_index(op.f("ix_workflow_step_executions_step_id"), "workflow_step_executions", ["step_id"], unique=False)
    op.create_index(op.f("ix_workflow_step_executions_status"), "workflow_step_executions", ["status"], unique=False)
    op.create_index("ix_workflow_step_executions_run_order", "workflow_step_executions", ["workflow_run_id", "order_index"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflow_step_executions_run_order", table_name="workflow_step_executions")
    op.drop_index(op.f("ix_workflow_step_executions_status"), table_name="workflow_step_executions")
    op.drop_index(op.f("ix_workflow_step_executions_step_id"), table_name="workflow_step_executions")
    op.drop_index(op.f("ix_workflow_step_executions_workflow_run_id"), table_name="workflow_step_executions")
    op.drop_table("workflow_step_executions")

    op.drop_index("ix_workflow_runs_workflow_created", table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_status"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_triggered_by"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_project_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_workflow_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")