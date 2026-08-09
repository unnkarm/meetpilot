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

from app.models.transcript import TranscriptSegment
from app.services.chat_service import _extract_citation, answer_question


class TestRAGChatService(unittest.TestCase):
    def setUp(self):
        self.meeting_id = uuid.uuid4()
        self.seg1 = TranscriptSegment(
            id=uuid.uuid4(),
            meeting_id=self.meeting_id,
            speaker="Alice",
            start_time=12.5,
            end_time=25.0,
            text="We finalized the cloud database migration budget at $45,000 for Q3.",
            embedding=[0.1] * 768,
        )
        self.seg2 = TranscriptSegment(
            id=uuid.uuid4(),
            meeting_id=self.meeting_id,
            speaker="Bob",
            start_time=45.0,
            end_time=60.0,
            text="Let's ensure the security audit is completed before the product release.",
            embedding=[0.2] * 768,
        )

    def test_extract_citation_from_answer(self):
        """Tests that explicit timestamps in LLM answers are extracted accurately."""
        answer = "The security audit was discussed at 00:45 by Bob."
        citation = _extract_citation(answer, self.seg2)
        self.assertEqual(citation, "00:45")

    def test_extract_citation_fallback_to_top_segment(self):
        """Tests that when no explicit timestamp is in text, top semantic segment timestamp is used."""
        answer = "The cloud database migration budget was set to $45,000."
        citation = _extract_citation(answer, self.seg1)
        self.assertEqual(citation, "00:12")

    def test_extract_citation_suppressed_on_negative_answer(self):
        """Tests that citations are NOT attached when LLM could not find information in meeting."""
        answer = "I couldn't find any mention of Kubernetes cluster scaling in this meeting."
        citation = _extract_citation(answer, self.seg1)
        self.assertIsNone(citation)

        answer2 = "The transcript does not contain information about office re-opening."
        citation2 = _extract_citation(answer2, self.seg1)
        self.assertIsNone(citation2)

    @patch("app.services.chat_service.generate_text")
    @patch("app.services.chat_service._retrieve_relevant_segments")
    def test_answer_question_successful_flow(self, mock_retrieve, mock_generate):
        """Tests end-to-end question answering flow with vector retrieval and grounding."""
        mock_retrieve.return_value = [self.seg1, self.seg2]
        mock_generate.return_value = "The team agreed on a $45,000 migration budget at 00:12."

        mock_db = MagicMock()
        answer, cited_ts = answer_question(mock_db, self.meeting_id, "What is the migration budget?")

        self.assertIn("$45,000", answer)
        self.assertEqual(cited_ts, "00:12")

    @patch("app.services.chat_service._retrieve_relevant_segments")
    def test_answer_question_empty_transcript(self, mock_retrieve):
        """Tests handling when meeting has no transcribed segments."""
        mock_retrieve.return_value = []
        mock_db = MagicMock()
        mock_db.query().filter().order_by().limit().all.return_value = []

        answer, cited_ts = answer_question(mock_db, self.meeting_id, "Who was speaking?")
        self.assertIn("couldn't find any transcribed content", answer)
        self.assertIsNone(cited_ts)


if __name__ == "__main__":
    unittest.main()
