"""remove password_hash and configure clerk auth schema

Revision ID: 001_remove_password_hash
Revises: 
Create Date: 2026-08-08 15:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_remove_password_hash'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop password_hash column if it exists in users
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if "users" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("users")]
        
        if "password_hash" in columns:
            op.drop_column("users", "password_hash")
            
        if "clerk_id" not in columns:
            op.add_column("users", sa.Column("clerk_id", sa.String(length=255), nullable=True))
            op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)
            
        if "avatar_url" not in columns:
            op.add_column("users", sa.Column("avatar_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "users" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("users")]
        if "password_hash" not in columns:
            op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
