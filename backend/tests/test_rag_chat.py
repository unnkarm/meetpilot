import unittest
import uuid
from unittest.mock import MagicMock, patch

from app.models.meeting import Meeting
from app.services.chat_service import answer_question
from app.services.knowledge_chat_service import GroundedAnswer
from app.services.knowledge_retriever import Evidence


class MeetingChatTests(unittest.TestCase):
    def setUp(self):
        self.meeting_id = uuid.uuid4()
        self.workspace_id = uuid.uuid4()
        self.db = MagicMock()
        self.db.get.return_value = Meeting(id=self.meeting_id, workspace_id=self.workspace_id,
                                            title="Budget", created_by=uuid.uuid4())

    @patch("app.services.chat_service.get_ai_provider")
    @patch("app.services.chat_service.KnowledgeRetriever")
    def test_citation_must_match_retrieved_meeting_segment(self, retriever_cls, provider_fn):
        retriever_cls.return_value.retrieve.return_value = [
            Evidence("transcript:one", "Alice: Budget is $45,000.",
                     {"type": "meeting", "meeting_id": str(self.meeting_id), "timestamp": "00:12"})]
        provider_fn.return_value.structured.return_value = GroundedAnswer(
            answer="The budget is $45,000.", source_ids=["transcript:one"])
        answer, timestamp = answer_question(self.db, self.meeting_id, "What budget?")
        self.assertIn("$45,000", answer)
        self.assertEqual(timestamp, "00:12")
        retriever_cls.return_value.retrieve.assert_called_once_with("What budget?", meeting_id=self.meeting_id)

    @patch("app.services.chat_service.KnowledgeRetriever")
    def test_empty_meeting_cannot_generate_answer(self, retriever_cls):
        retriever_cls.return_value.retrieve.return_value = []
        answer, timestamp = answer_question(self.db, self.meeting_id, "Unrecorded topic?")
        self.assertIn("enough evidence", answer)
        self.assertIsNone(timestamp)
