"""add agent_id to chat messages

Revision ID: 0009_chat_messages_agent_id
Revises: 0008_skills_schema
Create Date: 2026-07-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_chat_messages_agent_id"
down_revision = "0008_skills_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("agent_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_chat_messages_agent_id"), "chat_messages", ["agent_id"], unique=False)
    op.create_foreign_key(
        "fk_chat_messages_agent_id_resources",
        "chat_messages",
        "resources",
        ["agent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_chat_messages_agent_id_resources", "chat_messages", type_="foreignkey")
    op.drop_index(op.f("ix_chat_messages_agent_id"), table_name="chat_messages")
    op.drop_column("chat_messages", "agent_id")