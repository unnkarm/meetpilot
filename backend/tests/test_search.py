import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

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

from app.api.routes.search import search
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.transcript import TranscriptSegment
from app.models.user import User


class TestSearchService(unittest.TestCase):
    def setUp(self):
        self.workspace_id = uuid.uuid4()
        self.user = User(id=uuid.uuid4(), email="lead@meetpilot.ai", name="Lead Engineer")
        self.meeting_id = uuid.uuid4()
        self.meeting = Meeting(
            id=self.meeting_id,
            workspace_id=self.workspace_id,
            title="Q3 Infrastructure Planning",
            status=MeetingStatus.completed,
            created_by=self.user.id,
        )

    @patch("app.api.routes.search.get_user_workspace_ids")
    @patch("app.api.routes.search.embed_text")
    def test_hybrid_search_vector_and_keyword(self, mock_embed, mock_get_ws_ids):
        """Tests that search retrieves vector similarity results and keyword matches, scoped to workspace."""
        mock_get_ws_ids.return_value = [self.workspace_id]
        mock_embed.return_value = [0.1] * 768

        seg = TranscriptSegment(
            id=uuid.uuid4(),
            meeting_id=self.meeting_id,
            speaker="Sarah",
            start_time=30.0,
            end_time=45.0,
            text="We need to reduce engineering expenditure on cloud resources.",
            embedding=[0.1] * 768,
        )

        mock_db = MagicMock()
        # Mock vector query result
        mock_db.query().join().filter().order_by().limit().all.return_value = [
            (seg, self.meeting.title, None)
        ]
        # Mock keyword query results as empty to test vector result priority
        mock_db.query().filter().limit().all.return_value = []

        response = search(
            q="budget constraints",
            workspace_id=self.workspace_id,
            current_user=self.user,
            db=mock_db,
        )

        self.assertEqual(response.query, "budget constraints")
        self.assertTrue(len(response.results) >= 1)
        res = response.results[0]
        self.assertEqual(res.type, "transcript")
        self.assertEqual(res.speaker, "Sarah")
        self.assertEqual(res.timestamp, "00:30")
        self.assertIn("engineering expenditure", res.snippet)

    @patch("app.api.routes.search.get_user_workspace_ids")
    def test_search_isolation_blocks_unauthorized_workspace(self, mock_get_ws_ids):
        """Tests that searching a workspace the user does not belong to returns empty results."""
        mock_get_ws_ids.return_value = [self.workspace_id]
        unauthorized_ws = uuid.uuid4()

        mock_db = MagicMock()
        response = search(
            q="sensitive project code",
            workspace_id=unauthorized_ws,
            current_user=self.user,
            db=mock_db,
        )

        self.assertEqual(response.results, [])


if __name__ == "__main__":
    unittest.main()
