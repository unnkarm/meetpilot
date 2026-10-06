"""Selective live memory and speaker-aware extraction metadata.

Revision ID: 8d9f0123a4b5
Revises: 7c8e9f01a2b3
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8d9f0123a4b5"
down_revision = "7c8e9f01a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("tasks", "decisions"):
        existing = {column["name"] for column in inspector.get_columns(table)}
        if "source_speaker" not in existing:
            op.add_column(table, sa.Column("source_speaker", sa.String(255), nullable=True))
        if "extraction_confidence" not in existing:
            op.add_column(table, sa.Column("extraction_confidence", sa.Float(), nullable=True))
    if inspector.has_table("pilot_memories"):
        return
    op.create_table(
        "pilot_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcript_segments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Enum("commitment", "deadline", "fact", "important_context", name="pilotmemorykind"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_speaker", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("language_code", sa.String(12), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_segment_id", "kind", name="uq_pilot_memory_source_kind"),
    )
    op.create_index("ix_pilot_memories_meeting_id", "pilot_memories", ["meeting_id"])
    op.create_index("ix_pilot_memories_workspace_id", "pilot_memories", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_pilot_memories_workspace_id", table_name="pilot_memories")
    op.drop_index("ix_pilot_memories_meeting_id", table_name="pilot_memories")
    op.drop_table("pilot_memories")
    sa.Enum(name="pilotmemorykind").drop(op.get_bind(), checkfirst=True)
    op.drop_column("decisions", "extraction_confidence")
    op.drop_column("decisions", "source_speaker")
    op.drop_column("tasks", "extraction_confidence")
    op.drop_column("tasks", "source_speaker")
