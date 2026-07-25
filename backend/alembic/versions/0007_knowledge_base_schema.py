"""add knowledge base schema

Revision ID: 0007_knowledge_base_schema
Revises: 0006_provider_connections
Create Date: 2026-07-24

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "0007_knowledge_base_schema"
down_revision = "0006_provider_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("doc_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("upload_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_knowledge_id", "documents", ["knowledge_id"], unique=False)
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"], unique=False)
    op.create_index("ix_documents_knowledge_status", "documents", ["knowledge_id", "status"], unique=False)

    # Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(3072), nullable=True),
        sa.Column("embedding_status", sa.String(length=30), nullable=False),
        sa.Column("embedding_error", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"], unique=False)
    op.create_index("ix_document_chunks_knowledge_embedding", "document_chunks", ["knowledge_id", "embedding_status"], unique=False)

    # Create agent_knowledge_bindings table
    op.create_table(
        "agent_knowledge_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("similarity_threshold", sa.Float(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_knowledge_bindings_agent_id", "agent_knowledge_bindings", ["agent_id"], unique=False)
    op.create_index(
        "ix_agent_knowledge_bindings_agent_knowledge",
        "agent_knowledge_bindings",
        ["agent_id", "knowledge_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_knowledge_bindings_agent_knowledge", table_name="agent_knowledge_bindings")
    op.drop_index("ix_agent_knowledge_bindings_agent_id", table_name="agent_knowledge_bindings")
    op.drop_table("agent_knowledge_bindings")
    
    op.drop_index("ix_document_chunks_knowledge_embedding", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    
    op.drop_index("ix_documents_knowledge_status", table_name="documents")
    op.drop_index("ix_documents_file_hash", table_name="documents")
    op.drop_index("ix_documents_knowledge_id", table_name="documents")
    op.drop_table("documents")
