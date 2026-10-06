"""product_events

Revision ID: 3682a9195d1e
Revises: 49bdd5fdfe4c
Create Date: 2026-09-29 18:13:57.266425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3682a9195d1e'
down_revision: Union[str, None] = '49bdd5fdfe4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "product_events" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "product_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE")),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
    for name, columns in (("ix_product_events_user_id", ["user_id"]),
                          ("ix_product_events_workspace_id", ["workspace_id"]),
                          ("ix_product_events_name", ["name"])):
        if name not in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("product_events")}:
            op.create_index(name, "product_events", columns)


def downgrade() -> None:
    op.drop_table("product_events")
