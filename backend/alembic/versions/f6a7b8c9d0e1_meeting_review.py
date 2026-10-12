"""Evidence-linked review tools and workspace summary templates."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    # Bootstrap creates current metadata on fresh installations before Alembic.
    # Existing installations need these tables; skip already-created tables.
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "summary_templates" not in tables:
        op.create_table("summary_templates",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("instructions", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        op.create_index("ix_summary_templates_workspace_id", "summary_templates", ["workspace_id"])
    if "meeting_artifacts" not in tables:
        op.create_table("meeting_artifacts",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column("meeting_id", pg.UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("run_token", sa.String(36), nullable=True),
            sa.Column("options", pg.JSONB(), nullable=False),
            sa.Column("payload", pg.JSONB(), nullable=True),
            sa.Column("source_fingerprint", sa.String(64), nullable=True),
            sa.Column("ai_model", sa.String(255), nullable=True),
            sa.Column("prompt_version", sa.String(32), nullable=False),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        for column in ("meeting_id", "workspace_id", "created_by"):
            op.create_index("ix_meeting_artifacts_" + column, "meeting_artifacts", [column])
    if "meeting_bookmarks" not in tables:
        op.create_table("meeting_bookmarks",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column("meeting_id", pg.UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("label", sa.String(160), nullable=False),
            sa.Column("position_seconds", sa.Float(), nullable=False),
            sa.Column("source_segment_id", pg.UUID(as_uuid=True), sa.ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        op.create_index("ix_meeting_bookmarks_meeting_id", "meeting_bookmarks", ["meeting_id"])


def downgrade():
    op.drop_table("meeting_bookmarks")
    op.drop_table("meeting_artifacts")
    op.drop_table("summary_templates")
