"""add knowledge_documents and document_chunks tables with pgvector embeddings

Revision ID: 005_knowledge_documents
Revises: 004_live_meeting_fields
Create Date: 2026-08-09 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.models.transcript import Vector, EMBEDDING_DIM

revision: str = '005_knowledge_documents'
down_revision: Union[str, None] = '004_live_meeting_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create knowledge_documents table
    if "knowledge_documents" not in tables:
        op.create_table(
            "knowledge_documents",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "workspace_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=32), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )

    # 2. Create document_chunks table
    if "document_chunks" not in tables:
        op.create_table(
            "document_chunks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "document_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "workspace_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "document_chunks" in tables:
        op.drop_table("document_chunks")
    if "knowledge_documents" in tables:
        op.drop_table("knowledge_documents")
