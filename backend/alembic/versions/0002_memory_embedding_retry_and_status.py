"""memory embedding status and retry jobs

Revision ID: 0002_memory_embedding_retry_and_status
Revises: 0001_initial_schema
Create Date: 2026-06-03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_memory_embedding_retry_and_status"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memory_records",
        sa.Column("embedding_status", sa.String(length=30), nullable=False, server_default="pending"),
    )
    op.add_column("memory_records", sa.Column("embedding_provider", sa.String(length=30), nullable=True))
    op.add_column("memory_records", sa.Column("embedding_model", sa.String(length=120), nullable=True))
    op.add_column("memory_records", sa.Column("embedding_error", sa.Text(), nullable=True))
    op.add_column("memory_records", sa.Column("last_embedding_attempt_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(op.f("ix_memory_records_embedding_status"), "memory_records", ["embedding_status"], unique=False)

    op.execute(
        """
        UPDATE memory_records
        SET embedding_status = CASE
            WHEN embedding IS NULL THEN 'skipped'
            ELSE 'succeeded'
        END
        """
    )

    op.create_table(
        "memory_embedding_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("memory_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memory_embedding_jobs_memory_id"), "memory_embedding_jobs", ["memory_id"], unique=False)
    op.create_index(op.f("ix_memory_embedding_jobs_status"), "memory_embedding_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_memory_embedding_jobs_next_retry_at"), "memory_embedding_jobs", ["next_retry_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_memory_embedding_jobs_next_retry_at"), table_name="memory_embedding_jobs")
    op.drop_index(op.f("ix_memory_embedding_jobs_status"), table_name="memory_embedding_jobs")
    op.drop_index(op.f("ix_memory_embedding_jobs_memory_id"), table_name="memory_embedding_jobs")
    op.drop_table("memory_embedding_jobs")

    op.drop_index(op.f("ix_memory_records_embedding_status"), table_name="memory_records")
    op.drop_column("memory_records", "last_embedding_attempt_at")
    op.drop_column("memory_records", "embedding_error")
    op.drop_column("memory_records", "embedding_model")
    op.drop_column("memory_records", "embedding_provider")
    op.drop_column("memory_records", "embedding_status")
