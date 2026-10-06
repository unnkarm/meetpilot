"""local_ai_evidence_processing

Revision ID: 49bdd5fdfe4c
Revises: 005_knowledge_documents
Create Date: 2026-09-29 17:53:50.729281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49bdd5fdfe4c'
down_revision: Union[str, None] = '005_knowledge_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    op.execute("ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS 'transcribing'")
    op.execute("ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS 'transcribed'")
    op.execute("ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS 'embedding'")
    op.execute("ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS 'analyzing'")

    for table, columns in {
        "workspaces": [sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false())],
        "meetings": [sa.Column("processing_updated_at", sa.DateTime(timezone=True), nullable=True),
                     sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0")],
        "meeting_summaries": [sa.Column("ai_model", sa.String(255)), sa.Column("prompt_version", sa.String(50))],
        "tasks": [sa.Column("source_segment_id", sa.UUID(), nullable=True),
                  sa.Column("ai_model", sa.String(255)), sa.Column("prompt_version", sa.String(50))],
        "decisions": [sa.Column("source_segment_id", sa.UUID(), nullable=True),
                      sa.Column("ai_model", sa.String(255)), sa.Column("prompt_version", sa.String(50))],
        "transcript_segments": [sa.Column("embedding_model", sa.String(255))],
        "document_chunks": [sa.Column("embedding_model", sa.String(255))],
    }.items():
        existing = {column["name"] for column in sa.inspect(conn).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)

    for table in ("tasks", "decisions"):
        constraints = {tuple(fk["constrained_columns"]) for fk in sa.inspect(conn).get_foreign_keys(table)}
        constraint_name = f"fk_{table}_source_segment_id"
        if ("source_segment_id",) not in constraints:
            op.create_foreign_key(constraint_name, table, "transcript_segments", ["source_segment_id"], ["id"], ondelete="SET NULL")
        indexes = {index["name"] for index in sa.inspect(conn).get_indexes(table)}
        index_name = f"ix_{table}_source_segment_id"
        if index_name not in indexes:
            op.create_index(index_name, table, ["source_segment_id"])


def downgrade() -> None:
    for table in ("tasks", "decisions"):
        op.drop_index(f"ix_{table}_source_segment_id", table_name=table)
        op.drop_constraint(f"fk_{table}_source_segment_id", table_name=table, type_="foreignkey")
    for table, columns in {
        "document_chunks": ["embedding_model"],
        "transcript_segments": ["embedding_model"],
        "decisions": ["prompt_version", "ai_model", "source_segment_id"],
        "tasks": ["prompt_version", "ai_model", "source_segment_id"],
        "meeting_summaries": ["prompt_version", "ai_model"],
        "meetings": ["retry_count", "processing_updated_at"],
        "workspaces": ["is_demo"],
    }.items():
        for column in columns:
            op.drop_column(table, column)
    # PostgreSQL enum values cannot be removed safely while old rows may use them.
