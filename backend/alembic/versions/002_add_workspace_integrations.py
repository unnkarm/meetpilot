"""add workspace integrations table for discord google zoom

Revision ID: 002_workspace_integrations
Revises: 001_remove_password_hash
Create Date: 2026-08-08 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_workspace_integrations'
down_revision: Union[str, None] = '001_remove_password_hash'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "workspace_integrations" not in tables:
        op.create_table(
            "workspace_integrations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "workspace_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("provider", sa.String(length=50), nullable=False, index=True),
            sa.Column("is_connected", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("encrypted_config", sa.Text(), nullable=False),
            sa.Column("masked_identifier", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "workspace_integrations" in inspector.get_table_names():
        op.drop_table("workspace_integrations")
