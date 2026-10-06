"""Provider participant identities and explicit speaker mappings.

Revision ID: 9e0a1234b5c6
Revises: 8d9f0123a4b5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9e0a1234b5c6"
down_revision = "8d9f0123a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {item["name"] for item in inspector.get_columns("meeting_participants")}
    columns = [
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("provider_user_id", sa.String(255), nullable=True),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("identity_confidence", sa.Float(), nullable=True),
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column("meeting_participants", column)
    if not inspector.has_table("meeting_speaker_maps"):
        op.create_table(
            "meeting_speaker_maps",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("speaker_id", sa.String(255), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("evidence", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("meeting_id", "speaker_id", name="uq_meeting_speaker_map"),
        )
        op.create_index("ix_meeting_speaker_maps_meeting_id", "meeting_speaker_maps", ["meeting_id"])


def downgrade() -> None:
    op.drop_index("ix_meeting_speaker_maps_meeting_id", table_name="meeting_speaker_maps")
    op.drop_table("meeting_speaker_maps")
    for name in ("identity_confidence", "email_verified", "provider_email", "provider_user_id", "provider"):
        op.drop_column("meeting_participants", name)
