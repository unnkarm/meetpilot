"""Persist the workspace's local co-pilot voice selection."""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("workspaces")}
    if "pilot_voice_id" not in columns:
        op.add_column("workspaces", sa.Column("pilot_voice_id", sa.String(32), server_default="lessac", nullable=False))


def downgrade():
    op.drop_column("workspaces", "pilot_voice_id")
