"""Small local checks for the Pilot voice boundary; no model or server needed."""

import asyncio
import io
import struct
import unittest
import uuid
import wave
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from unittest.mock import AsyncMock

from app.services.pilot_audio import WebSocketAudioProvider
from app.services.pilot_identity import IdentityResolution, map_speaker_to_user, resolve_provider_identity
from app.services.pilot_phase1 import _task_action_and_deadline
from app.services.pilot_runtime import route_intent
from app.services.pilot_session import PilotSessionStore, PilotState
from app.services.pilot_streaming_stt import StreamingSpeechBuffer
from app.services.pilot_tts import _repack, _wav
from app.services.pilot_wakeword import TranscriptPhraseWakeWord
from app.services.knowledge_chat_service import answer_workspace_knowledge, INSUFFICIENT
from app.workers.meeting_bot import _is_admitted


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)


class FakeSTT:
    def transcribe(self, pcm):
        return "Hey Pilot, what did we agree on?", "en"


class PilotVoiceTests(unittest.TestCase):
    def test_wake_and_session_scoping(self):
        workspace, meeting, user = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        store = PilotSessionStore(FakeRedis())
        session = store.start(workspace, meeting, user)
        self.assertEqual(session.state, PilotState.LISTENING)
        self.assertEqual(TranscriptPhraseWakeWord().detect("Hello there"), None)
        self.assertEqual(TranscriptPhraseWakeWord().detect("Hey Pilot, what happened?"), "what happened?")
        self.assertIsNone(store.get(session.session_id, workspace, meeting, uuid.uuid4()))
        store.transition(session, PilotState.WAKE_DETECTED)
        store.transition(session, PilotState.PROCESSING)
        self.assertEqual(store.get(session.session_id, workspace, meeting, user).state, PilotState.PROCESSING)

    def test_speaker_mapping_requires_verified_resolution(self):
        db = MagicMock()
        meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
        db.query.return_value.join.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = []
        db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        self.assertIsNone(resolve_provider_identity(db, meeting, provider="native", email="unverified@example.com").user_id)
        self.assertIsNone(map_speaker_to_user(db, meeting, "Speaker 1", IdentityResolution()))
        db.get.return_value = object()
        db.query.return_value.filter.return_value.first.return_value = None
        known = uuid.uuid4()
        mapped = map_speaker_to_user(db, meeting, "Speaker 2", IdentityResolution(known, 0.99, "provider_user_id"))
        self.assertEqual(mapped.user_id, known)
        self.assertEqual(mapped.evidence, "provider_user_id")

    def test_incremental_stt_and_feedback_filter(self):
        buffer = StreamingSpeechBuffer(FakeSTT())
        voiced = struct.pack("<h", 5000) * 1600
        silence = b"\x00\x00" * 12000
        self.assertEqual(buffer.feed(voiced, assistant_originated=True), [])
        self.assertEqual(buffer.feed(voiced)[0].type, "speech_started")
        events = buffer.feed(silence)
        self.assertIn("final_transcript", [event.type for event in events])
        self.assertEqual(next(event for event in events if event.type == "final_transcript").speaker, "Speaker 1")
        self.assertIsNone(next(event for event in events if event.type == "final_transcript").confidence)

    def test_partial_and_final_include_every_pcm_frame(self):
        class CountingSTT:
            def __init__(self):
                self.lengths = []

            def transcribe(self, pcm):
                self.lengths.append(len(pcm))
                return "Review the migration", "en"

        stt = CountingSTT()
        buffer = StreamingSpeechBuffer(stt)
        voiced = struct.pack("<h", 5000) * 1600  # 100 ms at 16 kHz.
        events = []
        for _ in range(23):
            events.extend(buffer.feed(voiced))
        self.assertIn("partial_transcript", [event.type for event in events])
        for _ in range(7):
            events.extend(buffer.feed(b"\0\0" * 1600))
        self.assertIn("final_transcript", [event.type for event in events])
        self.assertEqual(stt.lengths[-1], 30 * len(voiced))

    def test_barge_in_is_emitted_before_transcription_and_accepts_followup(self):
        buffer = StreamingSpeechBuffer(FakeSTT())
        voiced = struct.pack("<h", 5000) * 1600
        self.assertEqual([event.type for event in buffer.feed(voiced, assistant_speaking=True)],
                         ["pilot_interrupted", "speech_started"])
        self.assertIn("final_transcript", [event.type for event in buffer.feed(b"\0\0" * 12000)])
        store = PilotSessionStore(FakeRedis())
        session = store.start(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
        store.transition(session, PilotState.WAKE_DETECTED)
        store.transition(session, PilotState.PROCESSING)
        store.transition(session, PilotState.SPEAKING)
        store.transition(session, PilotState.CAPTURING_QUERY)
        self.assertEqual(session.state, PilotState.CAPTURING_QUERY)

    def test_wav_chunks_have_exact_header_lengths(self):
        pcm = struct.pack("<h", 1200) * 1600
        chunk = _wav(pcm, 16000)
        self.assertEqual(len(chunk), 44 + len(pcm))
        with wave.open(io.BytesIO(chunk), "rb") as reader:
            self.assertEqual((reader.getframerate(), reader.getnframes()), (16000, 1600))
        self.assertEqual(_repack(chunk, 16000), chunk)

    def test_google_prejoin_is_not_reported_as_admitted(self):
        with patch("app.workers.meeting_bot._join_page_text", new=AsyncMock(
            return_value="what's your name? ask to join system info will be sent")):
            self.assertFalse(asyncio.run(_is_admitted(MagicMock(), "google_meet")))

    def test_audio_transport_marks_assistant_and_requires_playback_ack(self):
        websocket = MagicMock()
        websocket.send_json = unittest.mock.AsyncMock()
        websocket.send_bytes = unittest.mock.AsyncMock()
        asyncio.run(WebSocketAudioProvider(websocket).speak(b"RIFFfake"))
        self.assertEqual(websocket.send_json.call_args_list[0].args[0]["origin"], "pilot")
        self.assertTrue(websocket.send_json.call_args_list[-1].args[0]["ack_required"])
        websocket.send_bytes.assert_awaited_once()

    def test_routing_prefers_explicit_action(self):
        self.assertEqual(route_intent("create a task for John to update docs"), "action_request")
        self.assertEqual(route_intent("what is in our documents?"), "knowledge_question")
        self.assertEqual(route_intent("what did we just decide?"), "meeting_context_question")
        self.assertEqual(route_intent("What was our budget agreement in last week's meeting?"),
                         "historical_meeting_question")
        self.assertEqual(_task_action_and_deadline("review the PR by 2026-10-09"),
                         ("review the PR", "2026-10-09"))

    def test_workspace_rag_without_evidence_does_not_invent_answer(self):
        with patch("app.services.knowledge_chat_service.KnowledgeRetriever") as retriever:
            retriever.return_value.retrieve.return_value = []
            answer, citations = answer_workspace_knowledge(MagicMock(), uuid.uuid4(), "net profit last year")
        self.assertEqual(answer, INSUFFICIENT)
        self.assertEqual(citations, [])
