"""add project member permissions

Revision ID: 0005_project_member_permissions
Revises: 0004_runtime_runs_and_events
Create Date: 2026-06-04

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_project_member_permissions"
down_revision = "0004_runtime_runs_and_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_member_permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("can_add_members", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_member_permissions_project_user",
        "project_member_permissions",
        ["project_id", "user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_project_member_permissions_project_user", table_name="project_member_permissions")
    op.drop_table("project_member_permissions")
