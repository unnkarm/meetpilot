"""Evidence quotes and structured executive sections for native meetings.

Revision ID: a1b2c3d4e5f6
Revises: 9e0a1234b5c6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = "9e0a1234b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table, column in (
        ("tasks", sa.Column("source_quote", sa.Text(), nullable=True)),
        ("decisions", sa.Column("source_quote", sa.Text(), nullable=True)),
        ("meeting_summaries", sa.Column("executive_sections", postgresql.JSONB(), nullable=True)),
    ):
        names = {item["name"] for item in inspector.get_columns(table)}
        if column.name not in names:
            op.add_column(table, column)
    if "vexa_bot_id" in {item["name"] for item in inspector.get_columns("meetings")}:
        op.drop_column("meetings", "vexa_bot_id")


def downgrade() -> None:
    op.add_column("meetings", sa.Column("vexa_bot_id", sa.String(length=255), nullable=True))
    op.drop_column("meeting_summaries", "executive_sections")
    op.drop_column("decisions", "source_quote")
    op.drop_column("tasks", "source_quote")
