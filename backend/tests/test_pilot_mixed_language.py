"""Mixed-language voice/intelligence contracts without live models or Docker."""
import asyncio
import io
import struct
import unittest
import uuid
import wave
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.api.routes import pilot_voice, vexa_audio
from app.core.app_config import APP_CONFIG
from app.api.routes.pilot_voice import _followup_is_addressed
from app.core.config import settings
from app.database.base import Base
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingStatus, MeetingSummary
from app.models.task import Task, TaskStatus
from app.models.transcript import TranscriptSegment, Vector
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.services.knowledge_chat_service import GroundedAnswer, answer_workspace_knowledge
from app.services.knowledge_retriever import Evidence
from app.services.meeting_analysis import _dedupe_items, generate_meeting_insights, MeetingInsights, SummaryOnly
from app.services.meeting_signals import explicit_decision, first_person_commitment
from app.services.pilot_commands import NativeTaskRequest, native_task_command
from app.services.pilot_language import reply_language, script_languages
from app.services.pilot_phase1 import classify_live_statement, process_live_segment, answer_live_context
from app.services.pilot_runtime import route_intent, execute_pilot_query
from app.services.pilot_observability import PilotTrace
from app.services.pilot_streaming_stt import LocalWhisperSTT
from app.services.pilot_session import PilotSessionStore
from app.services.pilot_tts import (get_tts_provider, parse_voice_token, parse_voice_language,
                                     speech_spans, _wav)
from app.services.pilot_wakeword import TranscriptPhraseWakeWord
from app.workers.meeting_processor import _source_segment, process_transcript_intelligence


@compiles(ARRAY, "sqlite")
@compiles(JSONB, "sqlite")
@compiles(Vector, "sqlite")
def sqlite_test_type(element, compiler, **kwargs):
    return "TEXT"


class MixedLanguageTests(unittest.TestCase):
    def test_short_native_and_roman_questions_choose_reply_language(self):
        cases = [("কী সিদ্ধান্ত?", "bn"), ("কি niye আলোচনা?", "bn"),
                 ("क्या तय हुआ?", "hi"), ("humne kya decide kiya?", "hi"),
                 ("amra ki siddhanto niyechi?", "bn"), ("What did we decide?", "en"),
                 ("সারাংশটা in English বলুন", "en"), ("Explain the API in Hindi", "hi")]
        for question, expected in cases:
            self.assertEqual(reply_language(question), expected, question)
        self.assertEqual(script_languages("API আমরা শুক্রবার deploy করব। हमने budget तय किया।"), {"en", "bn", "hi"})
        self.assertEqual(script_languages("আমরা শুক্রবার যাব।"), {"bn"})
        self.assertEqual(reply_language("meeting er summary dao"), "bn")
        self.assertEqual(reply_language("meeting ka summary do"), "hi")

    def test_english_wake_survives_native_script_transcription(self):
        wake = TranscriptPhraseWakeWord()
        self.assertEqual(wake.detect("Pilot, আজকে আমরা কী সিদ্ধান্ত নিয়েছি?"), "আজকে আমরা কী সিদ্ধান্ত নিয়েছি?")
        self.assertEqual(wake.detect("পাইলট, কী আলোচনা হলো?"), "কী আলোচনা হলো?")
        self.assertEqual(wake.detect("पायलट, क्या तय हुआ?"), "क्या तय हुआ?")
        self.assertIsNone(wake.detect("আজ API নিয়ে আলোচনা করি"))

    def test_native_summary_history_and_document_scope(self):
        for text in ("মিটিংয়ের সারাংশ দাও", "আজ কী কী আলোচনা হলো?", "मीटिंग का सारांश बताओ", "मुख्य बातें बताओ"):
            self.assertEqual(route_intent(text), "summarize", text)
        self.assertEqual(route_intent("API migration নিয়ে কী সিদ্ধান্ত হলো?"), "meeting_context_question")
        self.assertEqual(route_intent("গত সপ্তাহের মিটিংয়ের সারাংশ বলো"), "historical_meeting_question")
        self.assertEqual(route_intent("इस डॉक्यूमेंट में क्या लिखा है?"), "knowledge_question")
        self.assertTrue(_followup_is_addressed("এটা ছোট করে বলো", "meeting"))
        self.assertTrue(_followup_is_addressed("और थोड़ा समझाओ", "meeting"))
        self.assertFalse(_followup_is_addressed("রাহুল এখন রিপোর্ট তৈরি করছে", "meeting"))

    def test_creation_requires_an_actual_imperative_and_not_background_speech(self):
        self.assertEqual(route_intent("John এর জন্য API review করার task তৈরি করো"), "action_request")
        self.assertEqual(route_intent("John के लिए API review का task बना दो"), "action_request")
        for text in ("আমরা John এর জন্য task তৈরি করবো", "John বলেছে task তৈরি করো", "John task बनाओगे"):
            self.assertNotEqual(route_intent(text), "action_request", text)

    def test_explicit_decisions_are_kept_in_all_three_languages(self):
        for text in ("We agreed to release on Friday.", "আমরা শুক্রবার API release করার সিদ্ধান্ত নিয়েছি।",
                     "हमने API release सोमवार को करने का फैसला किया।", "আমরা API migration Monday করব বলে ঠিক করেছি।"):
            candidate = classify_live_statement(text)
            self.assertIsNotNone(candidate, text)
            self.assertEqual(candidate.kind, "decision", text)
            self.assertEqual(candidate.text, text)
        for text in ("হয়তো PostgreSQL ব্যবহার করার সিদ্ধান্ত নিতে পারি।", "আমরা কি API release করার সিদ্ধান্ত নিয়েছি?",
                     "शायद हमने API release करने का फैसला किया।", "আমরা এখনও সিদ্ধান্ত নিইনি।", "क्या हमने फैसला किया?"):
            self.assertFalse(explicit_decision(text), text)

    def test_native_commitments_and_assigned_requests_preserve_original_text(self):
        for text in ("আমি API documentation review করব।", "मैं API documentation review करूँगा।"):
            self.assertTrue(first_person_commitment(text))
            self.assertEqual(classify_live_statement(text).kind, "commitment")
        self.assertFalse(first_person_commitment("আমি এই কাজ করব না।"))
        self.assertEqual(classify_live_statement("John, API documentation শুক্রবারের মধ্যে update করো।").assignee_name, "John")
        self.assertEqual(classify_live_statement("ডেডলাইন শুক্রবার দুপুর পর্যন্ত।").kind, "deadline")
        self.assertEqual(classify_live_statement("डेडलाइन सोमवार तक है।").kind, "deadline")
        self.assertIsNone(classify_live_statement("ডেডলাইন শুক্রবার নয়।"))
        self.assertEqual(classify_live_statement("সমস্যা: database access এখনও পাওয়া যায়নি।").kind, "important_context")

    def test_same_topic_different_decisions_do_not_get_deduplicated(self):
        decisions = [{"topic": "Release date", "outcome": "Friday", "source_quote": "Friday."},
                     {"topic": "Release date", "outcome": "Monday", "source_quote": "Monday."},
                     {"topic": "Release date", "outcome": "Monday", "source_quote": "Now Monday."}]
        self.assertEqual([row["outcome"] for row in _dedupe_items(decisions, "topic")], ["Friday", "Monday"])

    def test_long_meeting_rollup_is_bounded_and_retains_each_windows_decisions(self):
        merged, windows = [], []
        def structured(prompt, schema, system=""):
            if schema is MeetingInsights:
                index = len(windows); windows.append(prompt)
                return MeetingInsights(overview="এই অংশে আমরা সিদ্ধান্ত নিয়েছি। " * 15, key_takeaways=[], next_steps=[], tasks=[],
                    decisions=[{"topic": "Database", "outcome": f"Option {index}", "transcript_timestamp": f"00:{index:02d}",
                                "source_quote": f"We agreed to option {index}."}])
            merged.append(prompt.rsplit("without adding new facts:\n", 1)[1])
            return SummaryOnly(overview="সিদ্ধান্তগুলোর সারাংশ। " * 15, key_takeaways=[], next_steps=[])
        provider = MagicMock(); provider.structured.side_effect = structured
        configured = replace(APP_CONFIG, rag=replace(APP_CONFIG.rag, max_context_chars=300))
        transcript = "\n".join(f"[00:{i:02d}] John: We agreed to choose PostgreSQL option {i} for the next release." for i in range(20))
        with patch("app.services.meeting_analysis.APP_CONFIG", configured), \
             patch("app.services.meeting_analysis.get_ai_provider", return_value=provider):
            result = generate_meeting_insights(transcript, language_code="bn", language_name="Bengali")
        self.assertGreater(len(windows), 2)
        self.assertEqual(len(result["decisions"]), len(windows))
        self.assertGreater(len(merged), 1)
        self.assertTrue(all(len(digest) <= 300 for digest in merged))

    def test_streaming_and_live_stt_enable_code_switching_without_translation(self):
        model = MagicMock()
        text = "আমরা API release করব। हमने Monday तय किया।"
        model.transcribe.return_value = ([SimpleNamespace(text=text)], SimpleNamespace(language="bn"))
        stt = LocalWhisperSTT(); stt.model = model
        self.assertEqual(stt.transcribe(struct.pack("<h", 1000) * 1600, "auto")[0], text)
        options = model.transcribe.call_args.kwargs
        self.assertIsNone(options["language"])
        self.assertTrue(options["multilingual"])
        self.assertFalse(options["condition_on_previous_text"])
        self.assertEqual(options["task"], "transcribe")
        segment = SimpleNamespace(id=0, start=0, end=2, text=text, words=[], avg_logprob=-0.2,
                                  no_speech_prob=0, compression_ratio=1)
        model.transcribe.return_value = ([segment], SimpleNamespace(language="bn"))
        with patch.object(vexa_audio, "transcriber", return_value=stt):
            result = vexa_audio.transcribe_wav(_wav(b"\0\0" * 32000, 16000), "auto")
        self.assertEqual(result["text"], text)
        self.assertTrue(result["is_multilingual"])
        self.assertTrue(model.transcribe.call_args.kwargs["multilingual"])
        self.assertIsNone(model.transcribe.call_args.kwargs["language"])

    def test_native_language_travels_with_voice_id_and_cannot_be_injected(self):
        token = "mp/ryan/" + uuid.uuid4().hex + "/bn"
        self.assertEqual(parse_voice_token(token), "ryan")
        self.assertEqual(parse_voice_language(token), "bn")
        self.assertIsNone(parse_voice_language("mp/lessac/" + uuid.uuid4().hex))
        with self.assertRaises(ValueError):
            parse_voice_language("mp/ryan/" + uuid.uuid4().hex + "/../../secret")
        mixed = "আমরা API deploy করব। फिर budget review करेंगे।"
        spans = list(speech_spans(mixed, "bn"))
        self.assertEqual("".join(text for text, _ in spans), mixed)
        self.assertEqual([language for _, language in spans], ["bn", "hi"])

    def test_native_question_has_native_prompt_and_uncertainty(self):
        provider = MagicMock()
        provider.structured.return_value = GroundedAnswer(answer="সোমবার migration হবে [S1]।", source_ids=["S1"])
        with patch("app.services.knowledge_chat_service.get_ai_provider", return_value=provider), \
             patch("app.services.knowledge_chat_service.KnowledgeRetriever") as retriever:
            retriever.return_value.retrieve.return_value = [Evidence("turn:1", "सोमवार को migration तय हुआ।", {"timestamp": "00:05"})]
            answer, citations = answer_workspace_knowledge(MagicMock(), uuid.uuid4(), "কী সিদ্ধান্ত?")
        self.assertIn("Answer in Bengali", provider.structured.call_args.args[0])
        self.assertNotIn("S1", answer)
        self.assertEqual(citations[0]["timestamp"], "00:05")
        with patch("app.services.knowledge_chat_service.KnowledgeRetriever") as retriever:
            retriever.return_value.retrieve.return_value = []
            missing, _ = answer_workspace_knowledge(MagicMock(), uuid.uuid4(), "क्या तय हुआ?")
        self.assertIn("Uncertain", missing)
        self.assertIn("प्रमाण", missing)

    def test_private_live_tts_receives_native_language_and_pcm_format(self):
        seen = []
        class SpeechProvider:
            async def synthesize_chunks(self, text, language, sample_rate=24000):
                seen.append((text, language, sample_rate))
                yield _wav(b"\0\0" * 2400, 24000)
        app = FastAPI(); app.include_router(vexa_audio.router)
        with patch.object(settings, "VEXA_TTS_TOKEN", "private-test-token"), \
             patch.object(vexa_audio, "get_tts_provider", return_value=SpeechProvider()), TestClient(app) as client:
            response = client.post("/internal/vexa/v1/audio/speech", headers={"X-API-Key": "private-test-token"},
                                   json={"input": "কী সিদ্ধান্ত হয়েছে বলছি।", "voice": "mp/lessac/" + uuid.uuid4().hex + "/bn"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.content), 4800) # Raw PCM, not another RIFF header.
        self.assertEqual(seen[0][1:], ("bn", 24000))


class NativeSpeechTests(unittest.IsolatedAsyncioTestCase):
    async def test_english_neural_voice_is_not_used_for_hindi_or_bengali(self):
        calls = []
        async def neural(self, text, language=None, sample_rate=24000):
            calls.append(("neural", text, language)); yield _wav(b"\0\0" * 240, sample_rate)
        async def local(self, text, language=None, sample_rate=24000):
            calls.append(("local", text, language)); yield _wav(b"\0\0" * 240, sample_rate)
        with patch("app.services.pilot_tts.PiperTTS.synthesize_chunks", new=neural), \
             patch("app.services.pilot_tts.EspeakNGTTS.synthesize_chunks", new=local), \
             patch.dict("os.environ", {"PILOT_PIPER_HI_VOICE_PATH": "", "PILOT_PIPER_BN_VOICE_PATH": ""}):
            for text, language in (("We chose PostgreSQL.", "en"), ("हमने PostgreSQL तय किया।", "hi"), ("আমরা PostgreSQL ঠিক করেছি।", "bn")):
                chunks = [chunk async for chunk in get_tts_provider().synthesize_chunks(text, language)]
                with wave.open(io.BytesIO(chunks[0])) as wav:
                    self.assertEqual((wav.getframerate(), wav.getnframes()), (24000, 240))
        self.assertEqual([(engine, language) for engine, _, language in calls], [("neural", "en"), ("local", "hi"), ("local", "bn")])

    async def test_bengali_and_hindi_reply_language_reaches_playback_despite_english_asr_hint(self):
        class MemoryRedis:
            def __init__(self): self.rows = {}
            def setex(self, key, ttl, value): self.rows[key] = value
            def get(self, key): return self.rows.get(key)
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
        user = SimpleNamespace(id=uuid.uuid4())
        db = MagicMock(); db.__enter__.return_value = db; db.get.return_value = user
        for query, code in (("Pilot, কী সিদ্ধান্ত নিয়েছি?", "bn"), ("Pilot, क्या तय हुआ?", "hi")):
            store = PilotSessionStore(MemoryRedis()); session = store.start(meeting.workspace_id, meeting.id, user.id)
            socket = SimpleNamespace(send_json=AsyncMock())
            with patch.object(pilot_voice, "SessionLocal", return_value=db), \
                 patch.object(pilot_voice, "execute_pilot_query", return_value={"intent": "summarize", "answer": "A grounded reply.", "citations": []}), \
                 patch.object(pilot_voice, "_play_text", new_callable=AsyncMock) as output:
                completed = await pilot_voice._handle_final(socket, db, meeting, user, session, store,
                    query, "en", asyncio.Event(), {})
            self.assertTrue(completed)
            self.assertEqual(output.await_args.kwargs["language"], code)
            answer = next(call.args[0] for call in socket.send_json.call_args_list if call.args[0]["type"] == "answer")
            self.assertEqual(answer["reply_language"], code)

    async def test_native_meeting_voice_cannot_authorize_task_creation(self):
        class MemoryRedis:
            def __init__(self): self.rows = {}
            def setex(self, key, ttl, value): self.rows[key] = value
            def get(self, key): return self.rows.get(key)
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
        user = SimpleNamespace(id=uuid.uuid4())
        store = PilotSessionStore(MemoryRedis()); session = store.start(meeting.workspace_id, meeting.id, user.id)
        socket = SimpleNamespace(send_json=AsyncMock())
        with patch.object(pilot_voice, "execute_pilot_query") as query, \
             patch.object(pilot_voice, "_play_text", new_callable=AsyncMock):
            await pilot_voice._handle_final(socket, MagicMock(), meeting, user, session, store,
                "Pilot, John এর জন্য API review করার task তৈরি করো", "en", asyncio.Event(), {}, allow_actions=False)
        query.assert_not_called()
        answer = next(call.args[0] for call in socket.send_json.call_args_list if call.args[0]["type"] == "answer")
        self.assertIn("যাচাই", answer["answer"])
        self.assertEqual(answer["reply_language"], "bn")


class MixedMeetingPersistenceTests(unittest.TestCase):
    def setUp(self):
        # PostgreSQL ARRAY cannot bind lists in SQLite. Use JSON for just these
        # two test columns, retaining real PostgreSQL types in production.
        for name in ("key_takeaways", "next_steps"):
            column = MeetingSummary.__table__.c[name]
            variant = patch.object(column, "type", column.type.with_variant(JSON(), "sqlite"))
            variant.start()
            self.addCleanup(variant.stop)
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(id=uuid.uuid4(), name="John", clerk_id="test_mixed", email="john@example.com")
        self.db.add(self.user); self.db.flush()
        self.workspace = Workspace(id=uuid.uuid4(), name="Team", owner_id=self.user.id, is_demo=True)
        self.db.add(self.workspace); self.db.flush()
        self.db.add(WorkspaceMember(workspace_id=self.workspace.id, user_id=self.user.id, role=WorkspaceRole.owner))
        self.meeting = Meeting(id=uuid.uuid4(), workspace_id=self.workspace.id, created_by=self.user.id,
                               title="Mixed planning", source="live", status=MeetingStatus.in_progress, transcription_language="auto")
        self.db.add(self.meeting); self.db.flush()
        texts = ["We agreed to release on Friday.", "আমরা API migration সোমবার করব বলে ঠিক করেছি।",
                 "हमने budget को 5000 रखने का फैसला किया।"]
        self.segments = [TranscriptSegment(id=uuid.uuid4(), meeting_id=self.meeting.id, speaker="John", start_time=index * 20,
                                          end_time=index * 20 + 5, text=text) for index, text in enumerate(texts)]
        self.db.add_all(self.segments); self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def test_final_analysis_does_not_erase_live_decisions_or_completed_assigned_work(self):
        for segment in self.segments[:2]:
            process_live_segment(self.db, self.meeting, segment)
        task = Task(meeting_id=self.meeting.id, title="Review API", assignee_id=self.user.id, assignee_name="John", status=TaskStatus.done)
        self.db.add(task); self.db.commit(); task_id = task.id
        raw = [{"speaker": row.speaker, "start_time": row.start_time, "end_time": row.end_time, "text": row.text} for row in self.segments]
        insights = {"overview": "We discussed release, migration and budget.", "key_takeaways": [], "next_steps": [], "tasks": [],
                    "decisions": [{"topic": "Budget", "outcome": "Budget 5000", "transcript_timestamp": "00:40", "source_quote": self.segments[2].text}]}
        with patch("app.workers.meeting_processor.embed_texts", return_value=[None] * 3), \
             patch("app.workers.meeting_processor.generate_meeting_insights", return_value=insights), \
             patch("app.services.discord_service.post_meeting_digest_to_discord"):
            process_transcript_intelligence(self.db, self.meeting, raw)
            process_transcript_intelligence(self.db, self.meeting, raw)
        self.assertEqual(self.db.query(Decision).filter(Decision.meeting_id == self.meeting.id).count(), 3)
        self.assertEqual(self.db.get(Task, task_id).status, TaskStatus.done)
        self.assertEqual(self.db.get(Task, task_id).assignee_id, self.user.id)
        summary = self.db.query(MeetingSummary).filter(MeetingSummary.meeting_id == self.meeting.id).one()
        self.assertEqual(len(summary.executive_sections["key_decisions"]), 3)
        self.assertTrue(self.meeting.is_multilingual)

    def test_overlapping_speakers_are_selected_by_exact_native_quote(self):
        other = TranscriptSegment(id=uuid.uuid4(), meeting_id=self.meeting.id, speaker="Mira", start_time=20, end_time=25,
                                  text="मैं Friday को API review करूँगा।")
        self.assertIs(_source_segment("00:20", [self.segments[1], other], other.text), other)
        self.assertIsNone(_source_segment("00:20", [self.segments[1], other], "Invented quote for another speaker"))

    def test_native_task_parser_validates_quotes_owner_permissions_and_original_command(self):
        query = "John এর জন্য API review করার task শুক্রবারের মধ্যে তৈরি করো"
        provider = MagicMock(); provider.structured.return_value = NativeTaskRequest(assignee="John", action="API review", deadline_quote="শুক্রবার")
        with patch("app.services.pilot_commands.get_ai_provider", return_value=provider):
            result = execute_pilot_query(self.db, self.meeting.id, self.workspace.id, self.user, query, "Pilot",
                                        PilotTrace(self.meeting.id, self.workspace.id))
        task = self.db.get(Task, uuid.UUID(result["task_id"]))
        self.assertEqual(task.source_quote, query)
        self.assertEqual(task.assignee_id, self.user.id)
        self.assertIsNotNone(task.due_date)
        member = self.db.get(WorkspaceMember, (self.workspace.id, self.user.id)); member.role = WorkspaceRole.member; self.db.commit()
        with patch("app.services.pilot_commands.get_ai_provider") as model:
            with self.assertRaises(HTTPException):
                native_task_command(self.db, self.meeting, self.user, query)
        model.assert_not_called()

    def test_native_task_parser_rejects_invented_owner_or_partial_name(self):
        provider = MagicMock(); provider.structured.return_value = NativeTaskRequest(assignee="John", action="API review")
        with patch("app.services.pilot_commands.get_ai_provider", return_value=provider):
            with self.assertRaises(HTTPException):
                native_task_command(self.db, self.meeting, self.user, "Johnson এর জন্য API review task তৈরি করো")

    def test_native_summary_followup_uses_meeting_evidence_with_native_prompt(self):
        provider = MagicMock(); provider.structured.return_value = GroundedAnswer(answer="API migration সোমবার হবে।", source_ids=["S2"])
        with patch("app.services.pilot_phase1.get_ai_provider", return_value=provider):
            result = execute_pilot_query(self.db, self.meeting.id, self.workspace.id, self.user, "এটা ছোট করে বলো", "Pilot",
                                        PilotTrace(self.meeting.id, self.workspace.id), conversation_history=[
                                            {"role": "user", "content": "মিটিংয়ের সারাংশ দাও"},
                                            {"role": "assistant", "content": "Release, migration এবং budget নিয়ে আলোচনা হলো।"}])
        self.assertEqual(result["intent"], "summarize")
        self.assertIn("Answer in Bengali", provider.structured.call_args.args[0])
        self.assertEqual(result["citations"][0]["timestamp"], "00:20")
