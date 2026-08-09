import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Mock optional third-party modules if needed
for mod in ["pydantic_settings", "google", "google.genai", "google.genai.errors", "redis", "gradio_client"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

from fastapi import HTTPException
from app.api.deps import get_meeting_for_member
from app.api.routes.workspaces import remove_member, update_workspace
from app.models.meeting import Meeting, MeetingStatus
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import WorkspaceUpdate


class TestWorkspaceIsolationAndManagement(unittest.TestCase):
    def setUp(self):
        self.workspace_id = uuid.uuid4()
        self.owner = User(id=uuid.uuid4(), email="owner@meetpilot.ai", name="Workspace Owner")
        self.member = User(id=uuid.uuid4(), email="member@meetpilot.ai", name="Teammate")
        self.outsider = User(id=uuid.uuid4(), email="outsider@evil.corp", name="Malicious User")

        self.workspace = Workspace(id=self.workspace_id, name="Core Engineering", owner_id=self.owner.id)

        self.meeting = Meeting(
            id=uuid.uuid4(),
            workspace_id=self.workspace_id,
            title="Confidential Architecture Review",
            status=MeetingStatus.completed,
            created_by=self.owner.id,
        )

    def test_tenant_isolation_blocks_outsider(self):
        """Tests that get_meeting_for_member strictly blocks access for users not in the workspace."""
        mock_db = MagicMock()
        mock_db.get.side_effect = lambda model, key: {
            (Meeting, self.meeting.id): self.meeting,
            (WorkspaceMember, (self.workspace_id, self.outsider.id)): None,
        }.get((model, key))

        with self.assertRaises(HTTPException) as ctx:
            get_meeting_for_member(self.meeting.id, self.outsider, mock_db)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Not a member", ctx.exception.detail)

    def test_workspace_rename_success(self):
        """Tests that authorized owners/admins can rename a workspace."""
        mock_db = MagicMock()
        mock_db.get.return_value = self.workspace

        payload = WorkspaceUpdate(name="Platform Engineering")
        updated = update_workspace(self.workspace_id, payload, mock_db)

        self.assertEqual(updated.name, "Platform Engineering")
        mock_db.commit.assert_called_once()

    def test_remove_member_prevents_owner_removal(self):
        """Tests that the workspace owner cannot be removed via member deletion."""
        mock_db = MagicMock()
        mock_db.get.return_value = self.workspace

        with self.assertRaises(HTTPException) as ctx:
            remove_member(
                workspace_id=self.workspace_id,
                user_id=self.owner.id,
                current_user=self.owner,
                db=mock_db,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Cannot remove the workspace owner", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
