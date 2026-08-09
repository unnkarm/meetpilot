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

from app.models.document import KnowledgeDocument, DocumentChunk
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import TranscriptSegment
from app.services.knowledge_chat_service import answer_workspace_knowledge


class TestKnowledgeRAGService(unittest.TestCase):
    def setUp(self):
        self.workspace_id = uuid.uuid4()
        self.doc_id = uuid.uuid4()
        self.meeting_id = uuid.uuid4()

        self.doc_chunk = DocumentChunk(
            id=uuid.uuid4(),
            document_id=self.doc_id,
            workspace_id=self.workspace_id,
            chunk_index=0,
            page_number=3,
            text="Our Q4 product roadmap prioritizes vector search and enterprise SSO integration.",
            embedding=[0.1] * 768,
        )

        self.transcript_seg = TranscriptSegment(
            id=uuid.uuid4(),
            meeting_id=self.meeting_id,
            speaker="Sarah (Product Lead)",
            start_time=124.0,
            end_time=145.0,
            text="In the sprint review, we agreed to pull forward the SSO integration to Q3.",
            embedding=[0.15] * 768,
        )

    @patch("app.services.knowledge_chat_service.generate_text")
    @patch("app.services.knowledge_chat_service.embed_text")
    def test_cross_source_rag_document_and_meeting(self, mock_embed, mock_generate):
        """Tests that RAG retrieves both company document chunks and meeting transcript segments in the workspace."""
        mock_embed.return_value = [0.1] * 768
        mock_generate.return_value = (
            "According to the Product Roadmap (Page 3), enterprise SSO was originally scheduled for Q4. "
            "However, in the Sprint Review meeting @ 02:04, Sarah confirmed it has been pulled forward to Q3."
        )

        mock_db = MagicMock()

        # Differentiate queries in mock_db
        def mock_query(*entities):
            q = MagicMock()
            if any(e is DocumentChunk for e in entities):
                q.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
                    (self.doc_chunk, "Product_Roadmap.pdf")
                ]
            elif any(e is TranscriptSegment for e in entities):
                q.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
                    (self.transcript_seg, "Sprint Review", self.meeting_id)
                ]
            return q

        mock_db.query.side_effect = mock_query

        answer, citations = answer_workspace_knowledge(
            db=mock_db,
            workspace_id=self.workspace_id,
            question="What is the latest status of our SSO integration?",
        )

        self.assertIn("Product Roadmap", answer)
        self.assertIn("Sprint Review", answer)
        self.assertEqual(len(citations), 2)

        doc_cite = next(c for c in citations if c["type"] == "document")
        self.assertEqual(doc_cite["title"], "Product_Roadmap.pdf")
        self.assertEqual(doc_cite["page_number"], 3)

        meet_cite = next(c for c in citations if c["type"] == "meeting")
        self.assertEqual(meet_cite["title"], "Sprint Review")
        self.assertEqual(meet_cite["timestamp"], "02:04")
        self.assertEqual(meet_cite["speaker"], "Sarah (Product Lead)")

    def test_empty_workspace_knowledge(self):
        """Tests behavior when no matching documents or transcripts exist."""
        mock_db = MagicMock()
        mock_db.query().join().filter().order_by().limit().all.return_value = []
        mock_db.query().join().filter().limit().all.return_value = []

        answer, citations = answer_workspace_knowledge(
            db=mock_db,
            workspace_id=self.workspace_id,
            question="What is our travel reimbursement policy?",
        )

        self.assertIn("couldn't find any relevant company documents", answer)
        self.assertEqual(citations, [])


if __name__ == "__main__":
    unittest.main()
