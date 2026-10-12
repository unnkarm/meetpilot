"""Optional live PostgreSQL + Ollama multilingual retrieval smoke test.

Run with MEETPILOT_RUN_MULTILINGUAL_INTEGRATION=1. All inserted rows are rolled
back, so the application database is left unchanged.
"""

import os
import unittest
import uuid
from unittest.mock import patch

from app.core.app_config import APP_CONFIG
from app.database.session import SessionLocal
from app.models.document import DocumentChunk, KnowledgeDocument
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.workspace import Workspace
from app.services.embedding_provider import embed_text
from app.services.knowledge_chat_service import GroundedAnswer, answer_workspace_knowledge
from app.services.knowledge_retriever import KnowledgeRetriever


@unittest.skipUnless(os.getenv("MEETPILOT_RUN_MULTILINGUAL_INTEGRATION") == "1", "requires local PostgreSQL and Ollama")
class MultilingualIntegrationTests(unittest.TestCase):
    def test_cross_language_pgvector_retrieval_and_original_citation(self):
        db = SessionLocal()
        marker = uuid.uuid4().hex
        try:
            user = User(id=uuid.uuid4(), clerk_id="test_" + marker,
                        email=marker + "@test.invalid", name="Integration Test")
            db.add(user)
            db.flush()
            workspace = Workspace(id=uuid.uuid4(), name="Multilingual test", owner_id=user.id)
            db.add(workspace)
            db.flush()
            meeting = Meeting(id=uuid.uuid4(), workspace_id=workspace.id, created_by=user.id,
                              title="পরিকল্পনা", status=MeetingStatus.completed, language_code="bn")
            db.add(meeting)
            db.flush()
            speech = "আমরা আগামী মাসে নতুন onboarding system চালু করব।"
            segment = TranscriptSegment(
                id=uuid.uuid4(), meeting_id=meeting.id, speaker="SPEAKER_00",
                start_time=42.0, end_time=46.0, text=speech, language_code="bn",
                embedding=embed_text(speech), embedding_model=APP_CONFIG.embeddings.index_key,
            )
            db.add(segment)
            db.flush()

            question = "What are we launching next month?"
            evidence = KnowledgeRetriever(db, workspace.id).retrieve(question, meeting_id=meeting.id)
            self.assertTrue(any(item.id == f"transcript:{segment.id}" for item in evidence))
            self.assertIn(speech, next(item.text for item in evidence if item.id == f"transcript:{segment.id}"))

            document = KnowledgeDocument(
                id=uuid.uuid4(), workspace_id=workspace.id, title="हिंदी योजना",
                filename="plan.txt", file_type="txt", file_size=100, status="ready",
                chunk_count=1, created_by=user.id, language_code="hi",
            )
            db.add(document)
            db.flush()
            document_text = "अगले महीने नया onboarding system शुरू करेंगे।"
            chunk = DocumentChunk(
                id=uuid.uuid4(), document_id=document.id, workspace_id=workspace.id,
                chunk_index=0, page_number=1, text=document_text, language_code="hi",
                embedding=embed_text(document_text), embedding_model=APP_CONFIG.embeddings.index_key,
            )
            db.add(chunk)
            db.flush()

            provider = unittest.mock.MagicMock()
            provider.structured.return_value = GroundedAnswer(
                answer="A new onboarding system.", source_ids=[f"document:{chunk.id}"],
            )
            with patch("app.services.knowledge_chat_service.get_ai_provider", return_value=provider):
                answer, citations = answer_workspace_knowledge(db, workspace.id, question)
            self.assertIn("onboarding", answer)
            self.assertEqual(citations[0]["type"], "document")
            self.assertIn(document_text, citations[0]["snippet"])
        finally:
            db.rollback()
            db.close()
