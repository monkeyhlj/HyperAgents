"""add skills schema

Revision ID: 0008_skills_schema
Revises: 0007_knowledge_base_schema
Create Date: 2026-07-25

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0008_skills_schema"
down_revision = "0007_knowledge_base_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create skill_metadata table to extend resources for Skill kind
    op.create_table(
        "skill_metadata",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("storage_type", sa.String(length=30), nullable=False),  # "local" | "git" | "s3"
        sa.Column("repo_url", sa.String(length=500), nullable=True),  # For git/s3
        sa.Column("repo_branch", sa.String(length=100), default="main", nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=30), nullable=False),  # semantic versioning
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),  # list of capabilities
        sa.Column("requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),  # dict of dependencies
        sa.Column("entrypoint", sa.String(length=255), nullable=False),  # "scripts/main:execute"
        sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),  # JSON Schema
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),  # JSON Schema
        sa.Column("skill_md_content", sa.Text(), nullable=True),  # SKILL.md markdown content
        sa.Column("status", sa.String(length=30), default="active", nullable=False),  # "active" | "inactive" | "deprecated"
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skill_metadata_skill", "skill_metadata", ["skill_id"], unique=True)
    op.create_index("ix_skill_metadata_project_status", "skill_metadata", ["project_id", "status"])
    
    # Create agent_skill_bindings table
    op.create_table(
        "agent_skill_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("priority", sa.Integer(), default=0, nullable=False),
        sa.Column("instance_config", postgresql.JSONB(astext_type=sa.Text()), default={}, nullable=False),  # Override template config
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_skill_bindings_agent", "agent_skill_bindings", ["agent_id"])
    op.create_index("ix_agent_skill_bindings_skill", "agent_skill_bindings", ["skill_id"])
    op.create_index("ix_agent_skill_bindings_project", "agent_skill_bindings", ["project_id"])
    op.create_index(
        "ix_agent_skill_bindings_agent_skill",
        "agent_skill_bindings",
        ["agent_id", "skill_id"],
        unique=True
    )
    
    # Create skill_execution table for tracking skill runs
    op.create_table(
        "skill_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), default="pending", nullable=False),  # "pending" | "running" | "completed" | "failed"
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), default={}, nullable=False),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["resources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skill_executions_skill", "skill_executions", ["skill_id"])
    op.create_index("ix_skill_executions_agent", "skill_executions", ["agent_id"])
    op.create_index("ix_skill_executions_project", "skill_executions", ["project_id"])
    op.create_index("ix_skill_executions_status", "skill_executions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_skill_executions_status", table_name="skill_executions")
    op.drop_index("ix_skill_executions_project", table_name="skill_executions")
    op.drop_index("ix_skill_executions_agent", table_name="skill_executions")
    op.drop_index("ix_skill_executions_skill", table_name="skill_executions")
    op.drop_table("skill_executions")
    
    op.drop_index("ix_agent_skill_bindings_agent_skill", table_name="agent_skill_bindings")
    op.drop_index("ix_agent_skill_bindings_project", table_name="agent_skill_bindings")
    op.drop_index("ix_agent_skill_bindings_skill", table_name="agent_skill_bindings")
    op.drop_index("ix_agent_skill_bindings_agent", table_name="agent_skill_bindings")
    op.drop_table("agent_skill_bindings")
    
    op.drop_index("ix_skill_metadata_project_status", table_name="skill_metadata")
    op.drop_index("ix_skill_metadata_skill", table_name="skill_metadata")
    op.drop_table("skill_metadata")
