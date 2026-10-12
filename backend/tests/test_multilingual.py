"""Language metadata, original-language evidence, and retrieval contracts."""

import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.embedding_provider import OllamaEmbeddingProvider
from app.core.app_config import APP_CONFIG
from app.services.document_service import chunk_document_pages, extract_text_from_text_file
from app.services.knowledge_chat_service import GroundedAnswer, answer_workspace_knowledge
from app.services.knowledge_retriever import Evidence
from app.services.language_detection import detect_text_language
from app.services.meeting_analysis import ExtractedTask, MeetingInsights, _dedupe_items, generate_meeting_insights
from app.services.transcription import TranscriptionResult, transcribe_audio_with_metadata
from app.services.transcription import LocalWhisperProvider
from app.workers.meeting_processor import _supported_by_source


MEETINGS = {
    "en": "We agreed to use PostgreSQL. Rahul will update the API documentation by Friday.",
    "bn": "আমরা PostgreSQL ব্যবহার করার সিদ্ধান্ত নিয়েছি। রাহুল শুক্রবারের মধ্যে API documentation আপডেট করবে।",
    "hi": "हमने PostgreSQL इस्तेमाल करने का फैसला किया। राहुल शुक्रवार तक API documentation अपडेट करेगा।",
    "ta": "PostgreSQL பயன்படுத்த முடிவு செய்தோம். ராகுல் வெள்ளிக்கிழமைக்குள் API ஆவணத்தைப் புதுப்பிப்பார்.",
    "te": "PostgreSQL ఉపయోగించాలని నిర్ణయించుకున్నాం. రాహుల్ శుక్రవారం లోపు API డాక్యుమెంటేషన్‌ను నవీకరిస్తారు.",
    "mr": "आम्ही PostgreSQL वापरण्याचा निर्णय घेतला. राहुल शुक्रवारपर्यंत API कागदपत्रे अद्ययावत करेल.",
}

MIXED = [
    "राहुल, API documentation Friday तक update कर देना।",
    "আমরা এই feature টা next Friday deploy করব।",
    "நம்ம API endpoint ready ஆனதும் Friday deploy பண்ணலாம்.",
]


class MultilingualTests(unittest.TestCase):
    def test_text_detector_identifies_six_meeting_languages(self):
        for expected, text in MEETINGS.items():
            with self.subTest(expected=expected):
                result = detect_text_language(text)
                self.assertEqual(result.code, expected)
                self.assertGreaterEqual(result.confidence, 0.55)

    def test_code_switching_is_not_rewritten(self):
        for text in MIXED:
            with self.subTest(text=text):
                segment = {"speaker": "SPEAKER_00", "start_time": 1.0, "end_time": 4.0, "text": text}
                provider = MagicMock()
                provider.transcribe.return_value = TranscriptionResult([segment])
                with patch("app.services.transcription.get_transcription_provider", return_value=provider):
                    result = transcribe_audio_with_metadata(Path("meeting.wav"))
                self.assertEqual(result.segments[0]["text"], text)
                self.assertEqual(result.segments[0]["speaker"], "SPEAKER_00")

    def test_multilingual_document_text_remains_unicode_through_chunking(self):
        for code in ("bn", "hi", "ta", "te", "mr"):
            with self.subTest(code=code):
                pages = extract_text_from_text_file(MEETINGS[code].encode("utf-8"))
                chunks = chunk_document_pages(pages)
                self.assertEqual(chunks[0]["text"], MEETINGS[code])
                self.assertEqual(detect_text_language(chunks[0]["text"]).code, code)

    def test_local_whisper_uses_auto_transcribe_and_retains_language(self):
        segment = SimpleNamespace(start=0.3, end=3.0, text="আমরা PostgreSQL ব্যবহার করব।")
        info = SimpleNamespace(language="bn", language_probability=0.94)
        model = MagicMock()
        model.transcribe.return_value = ([segment], info)
        fake_module = SimpleNamespace(WhisperModel=MagicMock(return_value=model))
        with patch.dict("sys.modules", {"faster_whisper": fake_module}), \
             patch("app.services.transcription.split_audio", return_value=[
                 {"path": Path("chunk.wav"), "start_offset_ms": 0}
             ]), patch("app.services.transcription.cleanup_temp_chunks"):
            result = transcribe_audio_with_metadata(Path("meeting.wav"))
        self.assertEqual(result.language_code, "bn")
        self.assertIn("PostgreSQL", result.segments[0]["text"])
        self.assertEqual(model.transcribe.call_args.kwargs["language"], None)
        self.assertEqual(model.transcribe.call_args.kwargs["task"], "transcribe")
        self.assertTrue(model.transcribe.call_args.kwargs["multilingual"])

    def test_english_only_whisper_checkpoint_fails_for_multilingual_mode(self):
        configured = replace(APP_CONFIG, transcription=replace(APP_CONFIG.transcription, model="base.en"))
        with patch("app.services.transcription.APP_CONFIG", configured):
            with self.assertRaisesRegex(RuntimeError, "English-only"):
                transcribe_audio_with_metadata(Path("meeting.wav"))

    def test_whisper_capability_uses_real_language_codes(self):
        provider = LocalWhisperProvider()
        for code in ("en", "bn", "hi", "ta", "te", "mr", "gu", "pa", "ur"):
            self.assertTrue(provider.supports_language(code))
        self.assertFalse(provider.supports_language("zz"))

    def test_original_language_quote_is_required_for_paraphrase_evidence(self):
        source = SimpleNamespace(speaker="রাহুল", text="রাহুল শুক্রবারের মধ্যে API documentation আপডেট করবে।")
        self.assertTrue(_supported_by_source(
            "ডকুমেন্টেশন সংশোধন করো", source,
            "রাহুল শুক্রবারের মধ্যে API documentation আপডেট করবে।",
        ))
        self.assertFalse(_supported_by_source("Launch payment gateway", source, "not spoken"))

    def test_string_null_date_does_not_invent_a_due_date(self):
        task = ExtractedTask.model_validate({
            "title": "API documentation আপডেট করুন", "due_date": "null",
            "transcript_timestamp": "00:16",
        })
        self.assertIsNone(task.due_date)

    def test_summary_prompt_uses_meeting_language_and_date(self):
        provider = MagicMock()
        provider.structured.return_value = MeetingInsights(
            overview="PostgreSQL ব্যবহারের সিদ্ধান্ত হয়েছে।",
            key_takeaways=["API documentation আপডেট হবে।"],
            next_steps=["রাহুল কাজটি করবে।"],
            tasks=[], decisions=[],
        )
        with patch("app.services.meeting_analysis.get_ai_provider", return_value=provider):
            result = generate_meeting_insights(
                "[00:10] SPEAKER_00: " + MEETINGS["bn"], ["Rahul"], "bn", "Bengali", date(2026, 9, 30),
            )
        prompt = provider.structured.call_args.kwargs["prompt"]
        self.assertIn("Use Bengali", prompt)
        self.assertIn("2026-09-30", prompt)
        self.assertIn("original-language evidence", prompt)
        self.assertIn("PostgreSQL", prompt)
        self.assertIn("PostgreSQL", result["overview"])

    def test_repeated_action_is_not_saved_twice(self):
        tasks = [
            {"title": "API documentation আপডেট করুন", "source_quote": "আমি করব।"},
            {"title": "API documentation আপডেট করুন", "source_quote": "রাহুল, API documentation আপডেট করো।",
             "assignee_name": "Rahul"},
        ]
        selected = _dedupe_items(tasks, "title")
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["assignee_name"], "Rahul")

    def test_same_titled_actions_for_different_assignees_remain_distinct(self):
        tasks = [
            {"title": "Review API", "assignee_name": "Rahul", "source_quote": "Rahul will review API."},
            {"title": "Review API", "assignee_name": "Mira", "source_quote": "Mira will review API."},
        ]
        self.assertEqual(len(_dedupe_items(tasks, "title")), 2)

    def test_embedding_prefixes_distinguish_queries_from_documents(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value.json.return_value = {"embeddings": [[0.1] * 768]}
        with patch("app.services.embedding_provider.httpx.Client", return_value=client):
            OllamaEmbeddingProvider().embed([MEETINGS["hi"]], "RETRIEVAL_DOCUMENT")
            document_input = client.post.call_args.kwargs["json"]["input"][0]
            OllamaEmbeddingProvider().embed(["What was decided?"], "RETRIEVAL_QUERY")
            query_input = client.post.call_args.kwargs["json"]["input"][0]
        self.assertTrue(document_input.startswith("search_document: "))
        self.assertTrue(query_input.startswith("search_query: "))

    def test_bengali_question_keeps_original_evidence_citation(self):
        evidence = Evidence(
            "transcript:one", "SPEAKER_00: " + MEETINGS["bn"],
            {"type": "meeting", "title": "পরিকল্পনা", "meeting_id": "one",
             "timestamp": "00:10", "snippet": MEETINGS["bn"]},
        )
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(
            answer="PostgreSQL ব্যবহারের সিদ্ধান্ত হয়েছে।", source_ids=["transcript:one"],
        )
        with patch("app.services.knowledge_chat_service.KnowledgeRetriever") as retriever, \
             patch("app.services.knowledge_chat_service.get_ai_provider", return_value=provider):
            retriever.return_value.retrieve.return_value = [evidence]
            answer, citations = answer_workspace_knowledge(
                MagicMock(), MagicMock(), "মিটিংয়ে কোন ডেটাবেস ব্যবহার করার সিদ্ধান্ত নেওয়া হয়েছিল?"
            )
        self.assertIn("PostgreSQL", answer)
        self.assertEqual(citations[0]["timestamp"], "00:10")
        self.assertIn("Answer in Bengali", provider.structured.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
