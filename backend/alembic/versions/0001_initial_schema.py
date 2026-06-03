"""initial schema with pgvector memory

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-06-03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "project_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_members_project_user", "project_members", ["project_id", "user_id"], unique=True)

    op.create_table(
        "resources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("visibility", sa.String(length=30), nullable=False),
        sa.Column("model_provider", sa.String(length=60), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resources_project_id"), "resources", ["project_id"], unique=False)
    op.create_index(op.f("ix_resources_kind"), "resources", ["kind"], unique=False)
    op.create_index(op.f("ix_resources_visibility"), "resources", ["visibility"], unique=False)

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_sessions_project_id"), "chat_sessions", ["project_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_session_id"), "chat_messages", ["session_id"], unique=False)

    op.create_table(
        "memory_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("agent_id", sa.String(length=120), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("workflow_run_id", sa.String(length=120), nullable=True),
        sa.Column("memory_scope", sa.String(length=30), nullable=False),
        sa.Column("memory_type", sa.String(length=30), nullable=False),
        sa.Column("visibility", sa.String(length=30), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memory_records_agent_id"), "memory_records", ["agent_id"], unique=False)
    op.create_index(op.f("ix_memory_records_created_by"), "memory_records", ["created_by"], unique=False)
    op.create_index(op.f("ix_memory_records_memory_scope"), "memory_records", ["memory_scope"], unique=False)
    op.create_index(op.f("ix_memory_records_memory_type"), "memory_records", ["memory_type"], unique=False)
    op.create_index(op.f("ix_memory_records_project_id"), "memory_records", ["project_id"], unique=False)
    op.create_index(op.f("ix_memory_records_session_id"), "memory_records", ["session_id"], unique=False)
    op.create_index(op.f("ix_memory_records_visibility"), "memory_records", ["visibility"], unique=False)
    op.create_index(op.f("ix_memory_records_workflow_run_id"), "memory_records", ["workflow_run_id"], unique=False)
    op.create_index(
        "ix_memory_scope_project_created",
        "memory_records",
        ["memory_scope", "project_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_memory_scope_project_created", table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_workflow_run_id"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_visibility"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_session_id"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_project_id"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_memory_type"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_memory_scope"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_created_by"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_agent_id"), table_name="memory_records")
    op.drop_table("memory_records")

    op.drop_index(op.f("ix_chat_messages_session_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_chat_sessions_project_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.drop_index(op.f("ix_resources_visibility"), table_name="resources")
    op.drop_index(op.f("ix_resources_kind"), table_name="resources")
    op.drop_index(op.f("ix_resources_project_id"), table_name="resources")
    op.drop_table("resources")

    op.drop_index("ix_project_members_project_user", table_name="project_members")
    op.drop_table("project_members")

    op.drop_table("projects")
