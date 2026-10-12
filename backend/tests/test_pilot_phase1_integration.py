"""Rollback-only PostgreSQL check for selective Pilot persistence."""

import os
import unittest
import uuid
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.session import engine
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus
from app.models.pilot_memory import PilotMemory
from app.models.task import Task
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.services.pilot_phase1 import build_live_context, execute_explicit_task_command, process_live_segment
from app.services.knowledge_retriever import KnowledgeRetriever


@unittest.skipUnless(os.getenv("MEETPILOT_RUN_PILOT_INTEGRATION") == "1", "requires local PostgreSQL")
class PilotPhase1IntegrationTests(unittest.TestCase):
    def test_live_items_and_context_are_source_backed_and_workspace_scoped(self):
        connection = engine.connect()
        transaction = connection.begin()
        db = Session(bind=connection)
        try:
            marker = uuid.uuid4().hex
            host = User(id=uuid.uuid4(), clerk_id="pilot-host-" + marker, name="Rahul", email=f"host-{marker}@example.test")
            john = User(id=uuid.uuid4(), clerk_id="pilot-john-" + marker, name="John", email=f"john-{marker}@example.test")
            outsider = User(id=uuid.uuid4(), clerk_id="pilot-out-" + marker, name="Outsider", email=f"out-{marker}@example.test")
            db.add_all([host, john, outsider])
            db.flush()
            workspace = Workspace(id=uuid.uuid4(), name="Pilot test", owner_id=host.id)
            db.add(workspace)
            db.flush()
            db.add_all([
                WorkspaceMember(workspace_id=workspace.id, user_id=host.id, role=WorkspaceRole.owner),
                WorkspaceMember(workspace_id=workspace.id, user_id=john.id),
            ])
            meeting = Meeting(id=uuid.uuid4(), workspace_id=workspace.id, title="Pilot sprint", created_by=host.id,
                              status=MeetingStatus.in_progress, source="live")
            db.add(meeting)
            db.flush()
            db.add(MeetingParticipant(meeting_id=meeting.id, user_id=john.id, name="John", identity_verified_by=host.id, identity_confidence=1.0))
            db.flush()

            statements = [
                ("Speaker 1", "We could move to PostgreSQL.", 1.0),
                ("Speaker 1", "Okay, let's move to PostgreSQL.", 4.0),
                ("Rahul", "John, please update the API docs by 2026-10-05.", 8.0),
                ("Rahul", "Fact: The contract expires in October.", 12.0),
            ]
            for speaker, text, start in statements:
                segment = TranscriptSegment(id=uuid.uuid4(), meeting_id=meeting.id, speaker=speaker,
                                            start_time=start, end_time=start + 2.0, text=text, language_code="en")
                db.add(segment)
                db.flush()
                process_live_segment(db, meeting, segment)

            tasks = db.query(Task).filter(Task.meeting_id == meeting.id).all()
            decisions = db.query(Decision).filter(Decision.meeting_id == meeting.id).all()
            memories = db.query(PilotMemory).filter(PilotMemory.meeting_id == meeting.id).all()
            self.assertEqual(len(tasks), 1)
            self.assertEqual(len(decisions), 1)
            self.assertEqual(len(memories), 1)
            self.assertEqual(tasks[0].source_speaker, "Rahul")
            self.assertEqual(tasks[0].assignee_id, john.id)
            self.assertEqual(tasks[0].due_date, "2026-10-05")
            self.assertEqual(decisions[0].source_speaker, "Speaker 1")
            self.assertNotIn("could", decisions[0].outcome)
            context = build_live_context(db, meeting.id, host)
            self.assertEqual(len(context["recent_segments"]), 4)
            self.assertEqual(context["recent_memory"][0]["kind"], "fact")
            with patch("app.services.knowledge_retriever.embed_text", return_value=None):
                evidence = KnowledgeRetriever(db, workspace.id).retrieve("contract expires")
            self.assertTrue(any(item.id.startswith("memory:") and item.citation["timestamp"] == "00:12"
                                for item in evidence))
            created = execute_explicit_task_command(
                db, meeting.id, host, "Hey Pilot, create a task for John to prepare release notes."
            )
            self.assertEqual(created.assignee_id, john.id)
            self.assertEqual(created.title, "prepare release notes")
            with self.assertRaises(HTTPException) as denied:
                build_live_context(db, meeting.id, outsider)
            self.assertEqual(denied.exception.status_code, 403)
        finally:
            db.close()
            transaction.rollback()
            connection.close()


if __name__ == "__main__":
    unittest.main()
