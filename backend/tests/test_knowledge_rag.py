import unittest
import uuid
from unittest.mock import MagicMock, patch

from app.services.knowledge_chat_service import GroundedAnswer, INSUFFICIENT, answer_workspace_knowledge
from app.services.knowledge_retriever import Evidence


class KnowledgeRAGTests(unittest.TestCase):
    def setUp(self):
        self.workspace_id = uuid.uuid4()
        self.evidence = [
            Evidence("document:one", "The roadmap says SSO in Q4.",
                     {"type": "document", "title": "Roadmap", "document_id": "one", "snippet": "SSO in Q4"}),
            Evidence("transcript:two", "Alice: We decided to move SSO to Q3.",
                     {"type": "meeting", "title": "Sprint", "meeting_id": "two", "timestamp": "02:04", "snippet": "move SSO"}),
        ]

    @patch("app.services.knowledge_chat_service.get_ai_provider")
    @patch("app.services.knowledge_chat_service.KnowledgeRetriever")
    def test_cross_source_answer_returns_only_model_cited_sources(self, retriever_cls, provider_fn):
        retriever_cls.return_value.retrieve.return_value = self.evidence
        provider_fn.return_value.structured.return_value = GroundedAnswer(
            answer="The roadmap set Q4, then the sprint moved SSO to Q3.",
            source_ids=["document:one", "transcript:two"],
        )
        answer, citations = answer_workspace_knowledge(MagicMock(), self.workspace_id, "When is SSO?")
        self.assertIn("Q3", answer)
        self.assertEqual([c["type"] for c in citations], ["document", "meeting"])
        retriever_cls.assert_called_once()

    @patch("app.services.knowledge_chat_service.get_ai_provider")
    @patch("app.services.knowledge_chat_service.KnowledgeRetriever")
    def test_short_source_labels_resolve_to_real_citations(self, retriever_cls, provider_fn):
        retriever_cls.return_value.retrieve.return_value = self.evidence
        provider_fn.return_value.structured.return_value = GroundedAnswer(
            answer="The sprint moved SSO to Q3.", source_ids=["S2"])
        answer, citations = answer_workspace_knowledge(MagicMock(), self.workspace_id, "When is SSO?")
        self.assertIn("Q3", answer)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["meeting_id"], "two")
        prompt = provider_fn.return_value.structured.call_args.args[0]
        self.assertIn("[S2] Alice:", prompt)
        self.assertNotIn("[transcript:two]", prompt)

    @patch("app.services.knowledge_chat_service.get_ai_provider")
    @patch("app.services.knowledge_chat_service.KnowledgeRetriever")
    def test_fabricated_citation_is_rejected(self, retriever_cls, provider_fn):
        retriever_cls.return_value.retrieve.return_value = self.evidence
        provider_fn.return_value.structured.return_value = GroundedAnswer(
            answer="Unsupported answer", source_ids=["document:unknown"])
        answer, citations = answer_workspace_knowledge(MagicMock(), self.workspace_id, "Question")
        self.assertEqual(answer, INSUFFICIENT)
        self.assertEqual(citations, [])

    @patch("app.services.knowledge_chat_service.KnowledgeRetriever")
    def test_empty_workspace_does_not_call_llm(self, retriever_cls):
        retriever_cls.return_value.retrieve.return_value = []
        answer, citations = answer_workspace_knowledge(MagicMock(), self.workspace_id, "Unrecorded topic?")
        self.assertEqual(answer, INSUFFICIENT)
        self.assertEqual(citations, [])
