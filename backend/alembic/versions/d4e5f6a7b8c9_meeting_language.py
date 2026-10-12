"""Persist recognition language separately from detected speech and display."""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("meetings")}
    if "transcription_language" not in columns:
        op.add_column("meetings", sa.Column("transcription_language", sa.String(12), nullable=True))
    if "display_script" not in columns:
        op.add_column("meetings", sa.Column("display_script", sa.String(16), server_default="original", nullable=False))


def downgrade():
    op.drop_column("meetings", "display_script")
    op.drop_column("meetings", "transcription_language")
