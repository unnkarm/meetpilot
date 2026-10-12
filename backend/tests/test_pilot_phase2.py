"""Focused timing, recovery, and failure-isolation checks for Pilot."""

import unittest
import uuid
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes.pilot_phase1 import get_pilot_context
from app.core.app_config import APP_CONFIG
from app.models.meeting import MeetingStatus
from app.models.workspace import WorkspaceRole
from app.services.knowledge_chat_service import GroundedAnswer, INSUFFICIENT
from app.services.pilot_observability import PilotTrace
from app.services.pilot_phase1 import (
    answer_live_context,
    build_live_context,
    execute_explicit_task_command,
    process_live_segment,
    safely_process_live_segment,
)


class PilotPhase2Tests(unittest.TestCase):
    def test_stage_logs_ids_event_status_and_latency_without_content(self):
        trace = PilotTrace(uuid.uuid4(), uuid.uuid4())
        with patch("app.services.pilot_observability.logger.info") as logged:
            with trace.stage("retrieval"):
                secret = "Private contract amount"
        self.assertEqual(logged.call_count, 1)
        rendered = " ".join(map(str, logged.call_args.args))
        self.assertIn("retrieval", rendered)
        self.assertIn(str(trace.interaction_id), rendered)
        self.assertIn(str(trace.workspace_id), rendered)
        self.assertIn("ok", rendered)
        self.assertNotIn(secret, rendered)

    def test_failed_stage_records_error_and_reraises(self):
        trace = PilotTrace(uuid.uuid4(), uuid.uuid4())
        with patch("app.services.pilot_observability.logger.info") as logged:
            with self.assertRaisesRegex(RuntimeError, "offline"):
                with trace.stage("qwen_reasoning"):
                    raise RuntimeError("offline")
        self.assertIn("error", str(logged.call_args.args))

    def test_observability_switch_disables_events(self):
        trace = PilotTrace(uuid.uuid4(), uuid.uuid4())
        disabled = replace(APP_CONFIG, pilot=replace(APP_CONFIG.pilot, observability_enabled=False))
        with patch("app.services.pilot_observability.APP_CONFIG", disabled), \
             patch("app.services.pilot_observability.logger.info") as logged:
            with trace.stage("retrieval"):
                pass
        logged.assert_not_called()

    def test_pilot_disabled_blocks_context_and_passive_write(self):
        disabled = replace(APP_CONFIG, pilot=replace(APP_CONFIG.pilot, enabled=False))
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4(), status=MeetingStatus.in_progress)
        db = MagicMock()
        with patch("app.services.pilot_phase1.APP_CONFIG", disabled), \
             patch("app.services.pilot_phase1.get_meeting_for_member", return_value=meeting):
            with self.assertRaises(HTTPException) as denied:
                build_live_context(db, meeting.id, SimpleNamespace(id=uuid.uuid4()))
            self.assertIsNone(process_live_segment(db, meeting, SimpleNamespace(text="We decided to ship it.")))
        self.assertEqual(denied.exception.status_code, 503)
        db.add.assert_not_called()

    def test_passive_failure_rolls_back_without_raising(self):
        db = MagicMock()
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
        with patch("app.services.pilot_phase1.process_live_segment", side_effect=RuntimeError("database offline")), \
             patch("app.services.pilot_phase1.logger"):
            result = safely_process_live_segment(db, meeting, SimpleNamespace(id=uuid.uuid4()))
        self.assertIsNone(result)
        db.rollback.assert_called_once()

    def test_retrieval_failure_uses_live_turn_and_cited_answer(self):
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4(), title="Sprint")
        segment_id = str(uuid.uuid4())
        recent = {"id": segment_id, "speaker": "Rahul", "text": "We decided to ship Friday.",
                  "start_time": 10.0, "end_time": 12.0, "language_code": "en"}
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(answer="Friday.", source_ids=["transcript:" + segment_id])
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=meeting), \
             patch("app.services.pilot_phase1.build_live_context", return_value={"recent_segments": [recent]}), \
             patch("app.services.pilot_phase1.KnowledgeRetriever") as retriever, \
             patch("app.services.pilot_phase1.get_ai_provider", return_value=provider), \
             patch("app.services.pilot_phase1.logger"):
            retriever.return_value.retrieve.side_effect = RuntimeError("vector offline")
            result = answer_live_context(MagicMock(), meeting.id, SimpleNamespace(id=uuid.uuid4()), "When do we ship?")
        self.assertEqual(result["answer"], "Friday.")
        self.assertEqual(result["citations"][0]["timestamp"], "00:10")

    def test_retrieval_failure_without_recent_evidence_returns_insufficient(self):
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4(), title="Sprint")
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=meeting), \
             patch("app.services.pilot_phase1.build_live_context", return_value={"recent_segments": []}), \
             patch("app.services.pilot_phase1.KnowledgeRetriever") as retriever, \
             patch("app.services.pilot_phase1.get_ai_provider") as provider, \
             patch("app.services.pilot_phase1.logger"):
            retriever.return_value.retrieve.side_effect = RuntimeError("vector offline")
            result = answer_live_context(MagicMock(), meeting.id, SimpleNamespace(id=uuid.uuid4()), "When do we ship?")
        self.assertEqual(result, {"answer": INSUFFICIENT, "citations": []})
        provider.assert_not_called()

    def test_task_tool_failure_rolls_back_and_returns_controlled_error(self):
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
        db = MagicMock()
        db.get.return_value = SimpleNamespace(role=WorkspaceRole.owner)
        db.query.return_value.join.return_value.filter.return_value.all.return_value = [SimpleNamespace(id=uuid.uuid4(), name="John")]
        db.add.side_effect = RuntimeError("database offline")
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=meeting), \
             patch("app.services.pilot_phase1.logger"):
            with self.assertRaises(HTTPException) as failed:
                execute_explicit_task_command(db, meeting.id, SimpleNamespace(id=uuid.uuid4()),
                                              "Hey Pilot, create a task for John to update the API docs")
        self.assertEqual(failed.exception.status_code, 503)
        db.rollback.assert_called_once()

    def test_route_converts_unexpected_context_error_to_503(self):
        meeting_id = uuid.uuid4()
        with patch("app.api.routes.pilot_phase1.build_live_context", side_effect=RuntimeError("database offline")), \
             patch("app.api.routes.pilot_phase1.logger"):
            with self.assertRaises(HTTPException) as failed:
                get_pilot_context(meeting_id, current_user=SimpleNamespace(id=uuid.uuid4()), db=MagicMock())
        self.assertEqual(failed.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
