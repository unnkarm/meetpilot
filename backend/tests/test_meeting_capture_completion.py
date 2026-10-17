"""Natural meeting ends and interruptions preserve analysis and worker ownership."""
import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import redis
from app.core.config import settings
from app.models.meeting import MeetingStatus
from app.services.vexa_client import VexaError
from app.workers.vexa_meeting import BridgeSuperseded, finalize_capture, maintain_lease, run_vexa_meeting_bot_task


class CaptureCompletionTests(unittest.TestCase):
    def setUp(self):
        self.ident, self.workspace = uuid.uuid4(), uuid.uuid4()
        self.meeting = SimpleNamespace(id=self.ident, workspace_id=self.workspace,
            status=MeetingStatus.in_progress, audio_url=None, duration_seconds=None,
            failure_reason="old error", capture_failure_reason=None)
        self.db = MagicMock()
        self.db.get.return_value = self.meeting
        self.db.query().filter().scalar.return_value = 85.5

    def finish(self, failure=None, **kwargs):
        with patch("app.workers.vexa_meeting.SessionLocal") as factory, \
             patch("app.workers.meeting_processor.process_live_meeting.delay") as queue:
            factory.return_value.__enter__.return_value = self.db
            result = finalize_capture(self.ident, self.workspace, failure, **kwargs)
        return result, queue

    def test_normal_end_queues_saved_transcript_and_clears_error(self):
        result, queue = self.finish()
        self.assertTrue(result)
        self.assertEqual(self.meeting.status, MeetingStatus.queued)
        self.assertIsNone(self.meeting.failure_reason)
        self.assertIsNone(self.meeting.capture_failure_reason)
        self.assertEqual(self.meeting.duration_seconds, 85)
        queue.assert_called_once_with(str(self.ident))

    def test_unexpected_disconnect_still_analyzes_saved_evidence(self):
        result, queue = self.finish("Network disconnected")
        self.assertTrue(result)
        self.assertEqual(self.meeting.status, MeetingStatus.queued)
        self.assertEqual(self.meeting.capture_failure_reason, "Network disconnected")
        self.assertIsNone(self.meeting.failure_reason)
        queue.assert_called_once()

    def test_join_failure_without_evidence_remains_failed(self):
        self.db.query().filter().scalar.return_value = None
        result, queue = self.finish("Guest admission denied")
        self.assertFalse(result)
        self.assertEqual(self.meeting.status, MeetingStatus.failed)
        self.assertEqual(self.meeting.failure_reason, "Guest admission denied")
        queue.assert_not_called()

    def test_recording_can_be_analyzed_without_confirmed_turns(self):
        self.db.query().filter().scalar.return_value = None
        self.meeting.audio_url = "local://owned-recording.wav"
        result, queue = self.finish("Capture interrupted")
        self.assertTrue(result)
        queue.assert_called_once()

    def test_completed_or_foreign_workspace_is_not_mutated(self):
        self.meeting.status = MeetingStatus.completed
        result, queue = self.finish()
        self.assertFalse(result)
        self.db.commit.assert_not_called()
        queue.assert_not_called()
        self.meeting.status = MeetingStatus.in_progress
        self.meeting.workspace_id = uuid.uuid4()
        result, queue = self.finish()
        self.assertFalse(result)
        queue.assert_not_called()

    def test_queue_failure_is_an_analysis_error_not_a_bot_error(self):
        with patch("app.workers.vexa_meeting.SessionLocal") as factory, \
             patch("app.workers.meeting_processor.process_live_meeting.delay", side_effect=RuntimeError("broker offline")):
            factory.return_value.__enter__.return_value = self.db
            self.assertFalse(finalize_capture(self.ident, self.workspace))
        self.assertEqual(self.meeting.status, MeetingStatus.failed)
        self.assertIn("queue meeting analysis", self.meeting.failure_reason)
        self.assertIsNone(self.meeting.capture_failure_reason)

    def test_superseded_worker_does_not_stop_bot_or_fail_meeting(self):
        client = MagicMock()
        with patch("app.workers.vexa_meeting.redis.Redis.from_url", return_value=client), \
             patch("app.workers.vexa_meeting.SessionLocal") as factory, \
             patch("app.workers.vexa_meeting.run_bridge", new=AsyncMock(side_effect=BridgeSuperseded())), \
             patch("app.workers.vexa_meeting.VexaClient") as vexa, \
             patch("app.workers.vexa_meeting.finalize_capture") as finish, \
             patch("app.workers.vexa_meeting.status_event") as status:
            factory.return_value.__enter__.return_value = self.db
            run_vexa_meeting_bot_task.run(str(self.ident), "https://meet.google.com/abc-defg-hij")
        vexa.assert_not_called()
        finish.assert_not_called()
        status.assert_not_called()
        self.assertEqual(self.meeting.status, MeetingStatus.in_progress)

    def test_completed_provider_wins_over_transient_transport_error(self):
        client = MagicMock()
        with patch("app.workers.vexa_meeting.redis.Redis.from_url", return_value=client), \
             patch("app.workers.vexa_meeting.SessionLocal") as factory, \
             patch("app.workers.vexa_meeting.run_bridge", new=AsyncMock(side_effect=VexaError("late transport error"))), \
             patch("app.workers.vexa_meeting.maintain_lease", return_value=True), \
             patch("app.workers.vexa_meeting.sync_recording"), \
             patch("app.workers.vexa_meeting.VexaClient") as vexa, \
             patch("app.workers.vexa_meeting.finalize_capture") as finish, \
             patch("app.workers.vexa_meeting.status_event"):
            factory.return_value.__enter__.return_value = self.db
            vexa.return_value.meeting.return_value = {"status": "completed"}
            run_vexa_meeting_bot_task.run(str(self.ident), "https://meet.google.com/abc-defg-hij")
        finish.assert_called_once_with(self.ident, self.workspace, None)
        vexa.return_value.stop.assert_not_called()


@unittest.skipUnless(os.getenv("MEETPILOT_RUN_PILOT_INTEGRATION") == "1", "Redis integration disabled")
class CaptureLeaseTests(unittest.TestCase):
    def test_expired_lease_can_recover_but_cannot_steal_new_owner(self):
        client = redis.Redis.from_url(settings.REDIS_URL)
        key = "capture-regression:" + uuid.uuid4().hex
        try:
            self.assertTrue(maintain_lease(client, key, "original"))
            client.expire(key, 0)
            self.assertTrue(maintain_lease(client, key, "original"))
            client.set(key, "replacement", ex=30)
            self.assertFalse(maintain_lease(client, key, "original"))
            self.assertEqual(client.get(key), b"replacement")
            self.assertLessEqual(client.ttl(key), 30)
        finally:
            client.delete(key)
            client.close()
