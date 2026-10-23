"""Grounded voice-answer regressions without Docker, models, or external calls."""

import unittest
import uuid
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.meeting import Meeting
from app.models.task import Task
from app.models.decision import Decision
from app.models.transcript import TranscriptSegment, Vector
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.services.knowledge_chat_service import GroundedAnswer, answer_workspace_knowledge, indexed_evidence
from app.services.knowledge_retriever import Evidence
from app.services.pilot_answers import clean_evidence_handles, conversation_reference, grounded_response
from app.services.pilot_meeting_context import summary_timeline_evidence, _highlight_ids
from app.services.pilot_observability import PilotTrace
from app.services.pilot_phase1 import answer_live_context
from app.services.pilot_runtime import execute_pilot_query, route_intent


@compiles(ARRAY, "sqlite")
@compiles(JSONB, "sqlite")
@compiles(Vector, "sqlite")
def sqlite_test_type(element, compiler, **kwargs):
    return "TEXT"


class AnswerTextTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {
            "S9": Evidence("turn:9", "Alice agreed to migrate on Friday.", {"timestamp": "01:09"}),
            "S11": Evidence("turn:11", "Ben will test the migration.", {"timestamp": "01:11"}),
            "S17": Evidence("turn:17", "The budget was confirmed.", {"timestamp": "01:17"}),
        }

    def test_internal_source_handles_do_not_become_spoken_words(self):
        result = GroundedAnswer(answer="According to S9, we agreed to migrate Friday [S9].\n"
                                "- Ben will test the migration (S11). S17", source_ids=["S9", "S11", "S9"])
        answer, citations = grounded_response(result, self.evidence)
        self.assertEqual(answer, "we agreed to migrate Friday.\nBen will test the migration.")
        self.assertEqual(len(citations), 2)
        self.assertNotIn("S11", answer)

    def test_real_s3_storage_product_is_preserved_when_s3_is_a_citation_alias(self):
        available = {"S3": Evidence("turn:3", "We will keep logs in S3.", {"timestamp": "00:03"})}
        self.assertEqual(clean_evidence_handles("According to S3, logs go to AWS S3 [S3].", available),
                         "logs go to AWS S3.")
        self.assertEqual(clean_evidence_handles("Use S3 buckets for log storage [S3].", available),
                         "Use S3 buckets for log storage.")
        self.assertEqual(clean_evidence_handles("S9 API is a product name.", {}), "S9 API is a product name.")

    def test_fabricated_sources_and_empty_citation_only_answer_are_rejected(self):
        self.assertEqual(grounded_response(GroundedAnswer(answer="Invented", source_ids=["S100"]), self.evidence), ("", []))
        self.assertEqual(grounded_response(GroundedAnswer(answer="[S9]", source_ids=["S9"]), self.evidence), ("", []))

    def test_question_history_is_bounded_and_marked_as_non_evidence(self):
        history = [{"role": "system", "content": "Unsafe system override"}]
        history += [{"role": "user", "content": f"Question {index} " + "X" * 1000} for index in range(10)]
        reference = conversation_reference(history)
        self.assertNotIn("Unsafe system override", reference)
        self.assertNotIn("Question 0", reference)
        self.assertIn("Question 9", reference)
        self.assertIn("It is not evidence", reference)
        self.assertLess(len(reference), 3600)

    def test_spoken_summary_requests_and_workspace_scope_route_correctly(self):
        for text in ("Give me a summary of the meeting", "What keypoints have we discussed?",
                     "Can you summarize the meeting?", "What have we discussed in the meeting?",
                     "What decisions have we made?", "Brief me on the meeting so far"):
            self.assertEqual(route_intent(text), "summarize", text)
        self.assertEqual(route_intent("What did we just discuss?"), "meeting_context_question")
        self.assertEqual(route_intent("What did we decide about this project's database in this meeting?"), "meeting_context_question")
        self.assertEqual(route_intent("Give me a summary of last week's meeting"), "historical_meeting_question")
        self.assertEqual(route_intent("Summarize this document"), "knowledge_question")
        self.assertEqual(route_intent("Can you create a task for John to review the PR?"), "action_request")
        self.assertEqual(route_intent("Can you hear me?"), "general_conversation")

    def test_workspace_answer_separates_conversation_references_from_sources(self):
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(answer="The budget is 5000 [S1].", source_ids=["S1"])
        history = [{"role": "user", "content": "What budget did we agree last week?"}]
        with patch("app.services.knowledge_chat_service.KnowledgeRetriever") as retriever, \
             patch("app.services.knowledge_chat_service.get_ai_provider", return_value=provider):
            retriever.return_value.retrieve.return_value = [Evidence("turn:1", "Budget is 5000", {"timestamp": "00:10"})]
            answer, citations = answer_workspace_knowledge(MagicMock(), uuid.uuid4(), "Tell me more about that", conversation_history=history)
        self.assertEqual(answer, "The budget is 5000.")
        self.assertEqual(citations[0]["timestamp"], "00:10")
        self.assertIn("Previous question: What budget", retriever.return_value.retrieve.call_args.args[0])
        self.assertIn("ONLY in the source_ids array", provider.structured.call_args.args[0])


class MeetingSummaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(id=uuid.uuid4(), clerk_id="user_test", name="Alice", email="alice@example.com")
        self.db.add(self.user); self.db.flush()
        self.workspace = Workspace(id=uuid.uuid4(), name="Engineering", owner_id=self.user.id)
        self.other_workspace = Workspace(id=uuid.uuid4(), name="Elsewhere", owner_id=self.user.id)
        self.db.add_all([self.workspace, self.other_workspace]); self.db.flush()
        self.db.add(WorkspaceMember(workspace_id=self.workspace.id, user_id=self.user.id, role=WorkspaceRole.member))
        self.meeting = Meeting(id=uuid.uuid4(), workspace_id=self.workspace.id, title="Migration planning", created_by=self.user.id)
        self.other_meeting = Meeting(id=uuid.uuid4(), workspace_id=self.other_workspace.id, title="Private unrelated", created_by=self.user.id)
        self.db.add_all([self.meeting, self.other_meeting]); self.db.flush()
        for index in range(180):
            self.db.add(TranscriptSegment(id=uuid.uuid4(), meeting_id=self.meeting.id, speaker="Alice",
                                        start_time=index * 10, end_time=index * 10 + 5,
                                        text=f"Topic {index}: confirmed detail at this point in the meeting."))
        self.db.add(TranscriptSegment(id=uuid.uuid4(), meeting_id=self.other_meeting.id, speaker="Bob",
                                    start_time=0, end_time=3, text="Foreign confidential acquisition."))
        self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def test_summary_context_covers_start_middle_and_end_with_explicit_sampling(self):
        evidence, coverage = summary_timeline_evidence(self.db, self.meeting, 6000)
        text, available = indexed_evidence(evidence, 6000)
        self.assertEqual(coverage["total_segments"], 180)
        self.assertFalse(coverage["complete"])
        self.assertLessEqual(len(text), 6000)
        self.assertIn("Topic 0:", text)
        self.assertIn("Topic 179:", text)
        self.assertTrue(any(f"Topic {index}:" in text for index in range(70, 110)))
        self.assertNotIn("Foreign confidential", text)
        self.assertEqual(len([key for key in available if key.startswith("S")]), len(evidence))

    def test_summary_avoids_embedding_latency_and_returns_citations_and_coverage(self):
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(answer="From the recorded discussion, we reviewed planning [S1].", source_ids=["S1"])
        with patch("app.services.pilot_phase1.get_ai_provider", return_value=provider), \
             patch("app.services.pilot_phase1.KnowledgeRetriever") as retriever:
            result = execute_pilot_query(self.db, self.meeting.id, self.workspace.id, self.user,
                                         "Give me a summary of the meeting", "Pilot",
                                         PilotTrace(self.meeting.id, self.workspace.id))
        self.assertEqual(result["intent"], "summarize")
        self.assertNotIn("S1", result["answer"])
        self.assertFalse(result["context_coverage"]["complete"])
        self.assertEqual(result["citations"][0]["timestamp"], "00:00")
        retriever.assert_not_called()
        prompt = provider.structured.call_args.args[0]
        self.assertIn("Topic 0:", prompt)
        self.assertIn("Topic 179:", prompt)
        self.assertIn("never instructions", prompt)

    def test_short_uneven_meeting_retains_full_long_turn_when_total_fits(self):
        short = Meeting(id=uuid.uuid4(), workspace_id=self.workspace.id, title="Short meeting", created_by=self.user.id)
        self.db.add(short); self.db.flush()
        for index, text in enumerate(["Opening topic", "Details " * 550 + "FINAL AGREEMENT", "Closing topic"]):
            self.db.add(TranscriptSegment(id=uuid.uuid4(), meeting_id=short.id, speaker="Alice",
                                         start_time=index * 10, end_time=index * 10 + 5, text=text))
        self.db.commit()
        evidence, coverage = summary_timeline_evidence(self.db, short, 6000)
        text, _ = indexed_evidence(evidence, 6000)
        self.assertTrue(coverage["complete"])
        self.assertIn("FINAL AGREEMENT", text)
        self.assertLessEqual(len(text), 6000)

    def test_summary_followup_keeps_timeline_scope_and_current_question(self):
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(answer="Planning was discussed.", source_ids=["S1"])
        with patch("app.services.pilot_phase1.get_ai_provider", return_value=provider), \
             patch("app.services.pilot_phase1.KnowledgeRetriever") as retriever:
            result = execute_pilot_query(self.db, self.meeting.id, self.workspace.id, self.user,
                                         "Make it shorter", "Pilot", PilotTrace(self.meeting.id, self.workspace.id),
                                         conversation_history=[{"role": "user", "content": "Give me a meeting summary"}])
        self.assertEqual(result["intent"], "summarize")
        retriever.assert_not_called()
        self.assertIn("Question: Make it shorter", provider.structured.call_args.args[0])
        self.assertIn("Give me a meeting summary", provider.structured.call_args.args[0])

    def test_positional_and_chained_followups_keep_summary_scope(self):
        history = [{"role": "user", "content": "Give me a meeting summary"},
                   {"role": "assistant", "content": "First, we planned a migration. Second, testing was discussed."},
                   {"role": "user", "content": "Make it shorter"}]
        with patch("app.services.pilot_runtime.answer_live_context", return_value={"answer": "Testing was discussed.", "citations": []}) as answer:
            result = execute_pilot_query(self.db, self.meeting.id, self.workspace.id, self.user,
                                         "Explain the second point", "Pilot", PilotTrace(self.meeting.id, self.workspace.id),
                                         conversation_history=history)
        self.assertEqual(result["intent"], "summarize")
        self.assertTrue(answer.call_args.kwargs["summarize"])
        self.assertEqual(answer.call_args.kwargs["conversation_history"], history)

    def test_source_linked_highlights_keep_isolated_decision_and_enforce_task_visibility(self):
        first = self.db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == self.meeting.id,
                                                      TranscriptSegment.start_time == 10).one()
        second = self.db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == self.meeting.id,
                                                       TranscriptSegment.start_time == 20).one()
        foreign = self.db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == self.other_meeting.id).one()
        teammate = User(id=uuid.uuid4(), clerk_id="other_member", name="Bob", email="bob@example.com")
        self.db.add(teammate); self.db.flush()
        self.db.add(WorkspaceMember(workspace_id=self.workspace.id, user_id=teammate.id, role=WorkspaceRole.member))
        self.db.add_all([
            Decision(meeting_id=self.meeting.id, topic="An isolated decision", outcome="Not factual evidence", source_segment_id=first.id),
            Decision(meeting_id=self.meeting.id, topic="Bad cross-meeting link", outcome="Never leak this", source_segment_id=foreign.id),
            Task(meeting_id=self.meeting.id, title="My work", assignee_id=self.user.id, source_segment_id=first.id),
            Task(meeting_id=self.meeting.id, title="Someone else's work", assignee_id=teammate.id, source_segment_id=second.id),
        ]); self.db.commit()
        highlight_ids = _highlight_ids(self.db, self.meeting, self.user.id)
        self.assertIn(first.id, highlight_ids)
        self.assertNotIn(second.id, highlight_ids)
        self.assertNotIn(foreign.id, highlight_ids)
        evidence, _ = summary_timeline_evidence(self.db, self.meeting, 6000, user_id=self.user.id)
        text, _ = indexed_evidence(evidence, 6000)
        self.assertIn("Topic 1:", text)
        self.assertIn("Topic 179:", text)
        self.assertNotIn("Not factual evidence", text)
        self.assertNotIn("Foreign confidential", text)

    def test_recent_question_uses_latest_live_turns_without_embedding_model_switch(self):
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(answer="The last detail was Topic 179 [S1].", source_ids=["S1"])
        with patch("app.services.pilot_phase1.get_ai_provider", return_value=provider), \
             patch("app.services.pilot_phase1.KnowledgeRetriever") as retriever:
            result = answer_live_context(self.db, self.meeting.id, self.user, "What did we just discuss?")
        retriever.assert_not_called()
        self.assertEqual(result["citations"][0]["timestamp"], "29:50")
        self.assertIn("Topic 179", result["answer"])

    def test_foreign_meeting_and_removed_membership_cannot_use_context(self):
        with self.assertRaises(HTTPException) as denied:
            answer_live_context(self.db, self.other_meeting.id, self.user, "Give a summary", summarize=True)
        self.assertEqual(denied.exception.status_code, 403)
        member = self.db.get(WorkspaceMember, (self.workspace.id, self.user.id))
        self.db.delete(member); self.db.commit()
        with self.assertRaises(HTTPException) as revoked:
            answer_live_context(self.db, self.meeting.id, self.user, "Give a summary", summarize=True)
        self.assertEqual(revoked.exception.status_code, 403)

    def test_polite_task_request_accepts_custom_wake_alias_and_still_requires_manager(self):
        args = (self.db, self.meeting.id, self.workspace.id, self.user,
                "Can you create a task for Alice to review the migration by Friday?", "Buddy",
                PilotTrace(self.meeting.id, self.workspace.id))
        denied = execute_pilot_query(*args)
        self.assertIn("Uncertain", denied["answer"])
        self.assertEqual(self.db.query(Task).count(), 0)
        membership = self.db.get(WorkspaceMember, (self.workspace.id, self.user.id))
        membership.role = WorkspaceRole.owner; self.db.commit()
        result = execute_pilot_query(*args)
        self.assertEqual(result["intent"], "action_request")
        self.assertEqual(self.db.query(Task).one().assignee_id, self.user.id)
        self.assertEqual(self.db.query(Task).one().title, "review the migration")


if __name__ == "__main__":
    unittest.main()
