"""Persist original-language metadata without changing existing vectors.

Revision ID: 7c8e9f01a2b3
Revises: 3682a9195d1e
"""

from alembic import op
import sqlalchemy as sa

revision = "7c8e9f01a2b3"
down_revision = "3682a9195d1e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("language_code", sa.String(12), nullable=True))
    op.add_column("meetings", sa.Column("language_name", sa.String(80), nullable=True))
    op.add_column("meetings", sa.Column("language_confidence", sa.Float(), nullable=True))
    op.add_column("meetings", sa.Column("is_multilingual", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("transcript_segments", sa.Column("language_code", sa.String(12), nullable=True))
    op.add_column("knowledge_documents", sa.Column("language_code", sa.String(12), nullable=True))
    op.add_column("knowledge_documents", sa.Column("language_confidence", sa.Float(), nullable=True))
    op.add_column("document_chunks", sa.Column("language_code", sa.String(12), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "language_code")
    op.drop_column("knowledge_documents", "language_confidence")
    op.drop_column("knowledge_documents", "language_code")
    op.drop_column("transcript_segments", "language_code")
    op.drop_column("meetings", "is_multilingual")
    op.drop_column("meetings", "language_confidence")
    op.drop_column("meetings", "language_name")
    op.drop_column("meetings", "language_code")
