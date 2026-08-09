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

from app.api.routes.workspaces import get_workspace_analytics
from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task, TaskPriority, TaskStatus


class TestWorkspaceAnalytics(unittest.TestCase):
    def setUp(self):
        self.workspace_id = uuid.uuid4()
        self.meeting1 = Meeting(
            id=uuid.uuid4(),
            workspace_id=self.workspace_id,
            title="Design Sprint Sync",
            status=MeetingStatus.completed,
            duration_seconds=1800.0,
        )
        self.meeting2 = Meeting(
            id=uuid.uuid4(),
            workspace_id=self.workspace_id,
            title="Engineering Standup",
            status=MeetingStatus.completed,
            duration_seconds=1200.0,
        )
        self.task1 = Task(
            id=uuid.uuid4(),
            meeting_id=self.meeting1.id,
            title="Migrate database to pgvector",
            status=TaskStatus.done,
            priority=TaskPriority.high,
        )
        self.task2 = Task(
            id=uuid.uuid4(),
            meeting_id=self.meeting2.id,
            title="Configure Hugging Face ZeroGPU Space",
            status=TaskStatus.doing,
            priority=TaskPriority.medium,
        )

    def test_analytics_calculation(self):
        """Tests that workspace analytics calculates duration, tasks completion rate, and speaker airtime."""
        def mock_query(*entities):
            q = MagicMock()
            if len(entities) == 1 and entities[0] is Meeting:
                q.filter.return_value.all.return_value = [self.meeting1, self.meeting2]
            elif len(entities) == 1 and entities[0] is Task:
                q.join.return_value.filter.return_value.all.return_value = [self.task1, self.task2]
            elif len(entities) == 3:  # (TranscriptSegment.speaker, start_time, end_time)
                q.join.return_value.filter.return_value.all.return_value = [
                    ("Alex (Frontend)", 0.0, 60.0),
                    ("Jordan (Backend)", 60.0, 120.0),
                    ("Alex (Frontend)", 120.0, 150.0),
                ]
            else:
                q.join.return_value.filter.return_value.scalar.return_value = 5
                q.join.return_value.filter.return_value.all.return_value = []
            return q

        mock_db = MagicMock()
        mock_db.query.side_effect = mock_query

        analytics = get_workspace_analytics(self.workspace_id, mock_db)

        self.assertEqual(analytics.total_meetings, 2)
        self.assertEqual(analytics.completed_meetings, 2)
        self.assertEqual(analytics.total_speaking_seconds, 3000)
        self.assertEqual(analytics.total_speaking_hours, 0.83)
        self.assertEqual(analytics.avg_meeting_duration_minutes, 25.0)
        self.assertEqual(analytics.total_decisions, 5)
        self.assertEqual(analytics.total_tasks, 2)
        self.assertEqual(analytics.completed_tasks, 1)
        self.assertEqual(analytics.task_completion_rate, 50.0)

        # Check speaker airtime distribution
        self.assertTrue(len(analytics.speakers_distribution) >= 2)
        top_spk = analytics.speakers_distribution[0]
        self.assertEqual(top_spk.speaker, "Alex (Frontend)")
        self.assertEqual(top_spk.duration_seconds, 90.0)
        self.assertEqual(top_spk.turn_count, 2)
        self.assertEqual(top_spk.percentage, 60)


if __name__ == "__main__":
    unittest.main()
