"""add provider connections

Revision ID: 0006_provider_connections
Revises: 0005_project_member_permissions
Create Date: 2026-06-27

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0006_provider_connections"
down_revision = "0005_project_member_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("provider_type", sa.String(length=60), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("api_key_masked", sa.String(length=120), nullable=False),
        sa.Column("default_model", sa.String(length=120), nullable=True),
        sa.Column("model_list_cache", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_test_status", sa.String(length=30), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_connections_project_id"), "provider_connections", ["project_id"], unique=False)
    op.create_index(op.f("ix_provider_connections_owner_id"), "provider_connections", ["owner_id"], unique=False)
    op.create_index(
        "ix_provider_connections_project_name",
        "provider_connections",
        ["project_id", "name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_provider_connections_project_name", table_name="provider_connections")
    op.drop_index(op.f("ix_provider_connections_owner_id"), table_name="provider_connections")
    op.drop_index(op.f("ix_provider_connections_project_id"), table_name="provider_connections")
    op.drop_table("provider_connections")
