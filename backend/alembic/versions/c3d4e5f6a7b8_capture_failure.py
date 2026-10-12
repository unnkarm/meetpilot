"""Keep capture interruptions separate from meeting analysis status."""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("meetings")}
    if "capture_failure_reason" not in columns:
        op.add_column("meetings", sa.Column("capture_failure_reason", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("meetings", "capture_failure_reason")
