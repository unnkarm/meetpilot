"""Focused Phase 1 Pilot behavior without external services."""

import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.models.meeting import MeetingStatus
from app.models.workspace import WorkspaceRole
from app.services.pilot_phase1 import (
    _verified_participant,
    answer_live_context,
    build_live_context,
    classify_live_statement,
    execute_explicit_task_command,
    process_live_segment,
)
from app.services.knowledge_chat_service import GroundedAnswer


class PilotPhase1Tests(unittest.TestCase):
    def test_proposal_is_not_decision_but_explicit_agreement_is(self):
        self.assertIsNone(classify_live_statement("We could move to PostgreSQL."))
        self.assertIsNone(classify_live_statement("Should we move to PostgreSQL?"))
        accepted = classify_live_statement("Okay, let's move to PostgreSQL.")
        self.assertEqual(accepted.kind, "decision")
        self.assertGreaterEqual(accepted.confidence, 0.9)

    def test_task_preserves_addressee_and_safe_absolute_date(self):
        candidate = classify_live_statement("John, please update the API docs by 2026-10-05.")
        self.assertEqual(candidate.kind, "task")
        self.assertEqual(candidate.assignee_name, "John")
        self.assertEqual(candidate.due_date, "2026-10-05")
        self.assertIsNone(classify_live_statement("Let's talk about API docs."))

    def test_passive_memory_is_selective(self):
        self.assertIsNone(classify_live_statement("Hello, how are you doing?"))
        self.assertEqual(classify_live_statement("Fact: The contract expires in October.").kind, "fact")
        self.assertEqual(classify_live_statement("I commit to sending the proposal tomorrow.").kind, "commitment")

    def test_unknown_participant_never_becomes_user(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [SimpleNamespace(user_id=None)]
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
        self.assertIsNone(_verified_participant(db, meeting, "John"))

    def test_ambiguous_participant_name_stays_unknown(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [
            SimpleNamespace(user_id=uuid.uuid4()), SimpleNamespace(user_id=None),
        ]
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
        self.assertIsNone(_verified_participant(db, meeting, "John"))

    def test_verified_participant_can_be_assignee_without_changing_source_speaker(self):
        meeting_id, workspace_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        meeting = SimpleNamespace(id=meeting_id, workspace_id=workspace_id, status=MeetingStatus.in_progress)
        source = SimpleNamespace(id=uuid.uuid4(), speaker="Rahul", text="John, please update the API docs by 2026-10-05.", start_time=10.0)
        user = SimpleNamespace(id=user_id, name="John")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with patch("app.services.pilot_phase1._verified_participant", return_value=user):
            result = process_live_segment(db, meeting, source)
        self.assertEqual(result, "task")
        saved = db.add.call_args.args[0]
        self.assertEqual(saved.source_speaker, "Rahul")
        self.assertEqual(saved.assignee_id, user_id)
        self.assertEqual(saved.due_date, "2026-10-05")

    def test_unverified_addressee_keeps_task_unassigned(self):
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4(), status=MeetingStatus.in_progress)
        source = SimpleNamespace(id=uuid.uuid4(), speaker="Rahul", text="John, please update the API docs.", start_time=5.0)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with patch("app.services.pilot_phase1._verified_participant", return_value=None):
            process_live_segment(db, meeting, source)
        saved = db.add.call_args.args[0]
        self.assertIsNone(saved.assignee_id)
        self.assertEqual(saved.source_speaker, "Rahul")

    def test_context_is_bounded_and_meeting_authorized(self):
        meeting_id, workspace_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        meeting = SimpleNamespace(id=meeting_id, workspace_id=workspace_id, title="Sprint", language_code="hi")
        user = SimpleNamespace(id=user_id)
        segment = SimpleNamespace(id=uuid.uuid4(), speaker="Rahul", text="हमने API तय किया।", start_time=3.0, end_time=5.0, language_code="hi")
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.side_effect = [
            [segment], [], [], [],
        ]
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=meeting) as authorize:
            result = build_live_context(db, meeting_id, user)
        authorize.assert_called_once_with(meeting_id, user, db)
        self.assertEqual(result["recent_segments"][0]["text"], segment.text)
        self.assertEqual(result["active_speakers"], ["Rahul"])
        self.assertEqual(result["language_code"], "hi")

    def test_action_requires_direct_command_and_authorization(self):
        meeting_id = uuid.uuid4()
        db, user = MagicMock(), SimpleNamespace(id=uuid.uuid4())
        with patch("app.services.pilot_phase1.get_meeting_for_member", side_effect=HTTPException(403, "forbidden")):
            with self.assertRaises(HTTPException) as denied:
                execute_explicit_task_command(db, meeting_id, user, "Hey Pilot, create a task for John to update docs")
        self.assertEqual(denied.exception.status_code, 403)
        db.get.return_value = SimpleNamespace(role=WorkspaceRole.owner)
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=SimpleNamespace(id=meeting_id, workspace_id=uuid.uuid4())):
            with self.assertRaises(HTTPException) as discussion:
                execute_explicit_task_command(db, meeting_id, user, "We should create a task for John to update docs")
        self.assertEqual(discussion.exception.status_code, 422)

    def test_explicit_action_creates_scoped_evidence_linked_task(self):
        meeting_id, workspace_id = uuid.uuid4(), uuid.uuid4()
        user = SimpleNamespace(id=uuid.uuid4())
        member = SimpleNamespace(id=uuid.uuid4(), name="John")
        db = MagicMock()
        db.get.return_value = SimpleNamespace(role=WorkspaceRole.owner)
        db.query.return_value.join.return_value.filter.return_value.all.return_value = [member]
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=SimpleNamespace(id=meeting_id, workspace_id=workspace_id)):
            execute_explicit_task_command(db, meeting_id, user, "Hey Pilot, create a task for John to update the API docs by 2026-10-09.")
        task = db.add.call_args.args[0]
        self.assertEqual(task.meeting_id, meeting_id)
        self.assertEqual(task.assignee_id, member.id)
        self.assertEqual(task.title, "update the API docs")
        self.assertEqual(task.due_date, "2026-10-09")
        self.assertIn("John", task.source_quote)
        db.commit.assert_called_once()

    def test_multilingual_live_answer_uses_recent_source_and_citation(self):
        meeting_id, workspace_id = uuid.uuid4(), uuid.uuid4()
        meeting = SimpleNamespace(id=meeting_id, workspace_id=workspace_id, title="পরিকল্পনা")
        segment_id = str(uuid.uuid4())
        recent = {"id": segment_id, "speaker": "Rahul", "text": "আমরা PostgreSQL ব্যবহার করার সিদ্ধান্ত নিয়েছি।",
                  "start_time": 10.0, "end_time": 15.0, "language_code": "bn"}
        db, user = MagicMock(), SimpleNamespace(id=uuid.uuid4())
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(answer="PostgreSQL ব্যবহারের সিদ্ধান্ত হয়েছে।", source_ids=["transcript:" + segment_id])
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=meeting), \
             patch("app.services.pilot_phase1.build_live_context", return_value={"recent_segments": [recent]}), \
             patch("app.services.pilot_phase1.KnowledgeRetriever") as retriever, \
             patch("app.services.pilot_phase1.get_ai_provider", return_value=provider):
            retriever.return_value.retrieve.return_value = []
            result = answer_live_context(db, meeting_id, user, "কী সিদ্ধান্ত হয়েছে?")
        self.assertIn("PostgreSQL", result["answer"])
        self.assertEqual(result["citations"][0]["timestamp"], "00:10")

    def test_live_answer_rejects_fabricated_source_id(self):
        meeting_id, workspace_id = uuid.uuid4(), uuid.uuid4()
        meeting = SimpleNamespace(id=meeting_id, workspace_id=workspace_id, title="Sprint")
        recent = {"id": str(uuid.uuid4()), "speaker": "Rahul", "text": "We decided on PostgreSQL.",
                  "start_time": 10.0, "end_time": 15.0, "language_code": "en"}
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(answer="Invented answer", source_ids=["fabricated"])
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=meeting), \
             patch("app.services.pilot_phase1.build_live_context", return_value={"recent_segments": [recent]}), \
             patch("app.services.pilot_phase1.KnowledgeRetriever") as retriever, \
             patch("app.services.pilot_phase1.get_ai_provider", return_value=provider):
            retriever.return_value.retrieve.return_value = []
            result = answer_live_context(MagicMock(), meeting_id, SimpleNamespace(id=uuid.uuid4()), "What did we decide?")
        self.assertEqual(result["citations"], [])
        self.assertNotEqual(result["answer"], "Invented answer")

    def test_live_answer_handles_model_failure_without_citation(self):
        meeting_id, workspace_id = uuid.uuid4(), uuid.uuid4()
        meeting = SimpleNamespace(id=meeting_id, workspace_id=workspace_id, title="Sprint")
        recent = {"id": str(uuid.uuid4()), "speaker": "Rahul", "text": "We decided on PostgreSQL.",
                  "start_time": 10.0, "end_time": 15.0, "language_code": "en"}
        provider = MagicMock()
        provider.structured.side_effect = RuntimeError("model unavailable")
        with patch("app.services.pilot_phase1.get_meeting_for_member", return_value=meeting), \
             patch("app.services.pilot_phase1.build_live_context", return_value={"recent_segments": [recent]}), \
             patch("app.services.pilot_phase1.KnowledgeRetriever") as retriever, \
             patch("app.services.pilot_phase1.logger"), \
             patch("app.services.pilot_phase1.get_ai_provider", return_value=provider):
            retriever.return_value.retrieve.return_value = []
            result = answer_live_context(MagicMock(), meeting_id, SimpleNamespace(id=uuid.uuid4()), "What did we decide?")
        self.assertEqual(result["citations"], [])
        self.assertIn("reliable answer", result["answer"])


if __name__ == "__main__":
    unittest.main()
