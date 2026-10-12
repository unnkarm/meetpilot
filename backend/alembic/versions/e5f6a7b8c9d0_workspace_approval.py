"""Manager approval, join codes, and verified identity metadata."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    # Repair ownership after the old unrestricted role-update endpoint.
    op.execute("UPDATE workspace_members AS m SET role = 'admin' FROM workspaces AS w WHERE m.workspace_id = w.id AND m.role = 'owner' AND m.user_id <> w.owner_id")
    op.execute("UPDATE workspace_members AS m SET role = 'owner' FROM workspaces AS w WHERE m.workspace_id = w.id AND m.user_id = w.owner_id")
    inspector = sa.inspect(op.get_bind())
    columns = {table: {c["name"] for c in inspector.get_columns(table)}
               for table in ("workspaces", "users", "meeting_participants")}
    if "join_code_hash" not in columns["workspaces"]:
        op.add_column("workspaces", sa.Column("join_code_hash", sa.String(64), nullable=True))
    if not any(set(constraint["column_names"]) == {"join_code_hash"}
               for constraint in inspector.get_unique_constraints("workspaces")):
        op.create_unique_constraint("uq_workspace_join_code", "workspaces", ["join_code_hash"])
    if "join_code_expires_at" not in columns["workspaces"]:
        op.add_column("workspaces", sa.Column("join_code_expires_at", sa.DateTime(timezone=True), nullable=True))
    if "email_verified" not in columns["users"]:
        op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    if "identity_verified_by" not in columns["meeting_participants"]:
        op.add_column("meeting_participants", sa.Column("identity_verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    if "workspace_join_requests" not in inspector.get_table_names():
        op.create_table("workspace_join_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_join_user"))
        op.create_index("ix_workspace_join_requests_workspace_id", "workspace_join_requests", ["workspace_id"])
        op.create_index("ix_workspace_join_requests_user_id", "workspace_join_requests", ["user_id"])
    # Name-only AI guesses must not grant assignment access. Managers can
    # confirm them again; preserve the proposed name and source evidence.
    op.execute("UPDATE tasks SET assignee_id = NULL WHERE source_segment_id IS NOT NULL AND ai_model IS NOT NULL AND COALESCE(prompt_version, '') NOT LIKE 'pilot-explicit%'")


def downgrade():
    op.drop_table("workspace_join_requests")
    op.drop_column("meeting_participants", "identity_verified_by")
    op.drop_column("users", "email_verified")
    op.drop_column("workspaces", "join_code_expires_at")
    op.drop_constraint("uq_workspace_join_code", "workspaces", type_="unique")
    op.drop_column("workspaces", "join_code_hash")
