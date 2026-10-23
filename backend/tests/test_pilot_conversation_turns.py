"""Voice conversation regressions without speech models, Redis, or Docker."""
import asyncio
import json
import threading
import unittest
import uuid
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes import pilot_voice
from app.core.app_config import APP_CONFIG
from app.models.meeting import MeetingStatus
from app.services.pilot_session import PilotSessionStore, PilotState
from app.services.pilot_streaming_stt import SpeechEvent
from app.services.pilot_wakeword import WakeGate


class MemoryRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)


class FakeSocket:
    def __init__(self, session_id):
        self.session_id = session_id
        self.frames = asyncio.Queue()
        self.events = []
        self.changed = asyncio.Event()

    async def accept(self):
        pass

    async def receive_json(self):
        return {"token": "verified", "session_id": self.session_id, "input_source": "microphone"}

    async def receive(self):
        return await self.frames.get()

    async def send_json(self, value):
        self.events.append(value)
        self.changed.set()

    async def send_bytes(self, value):
        pass

    async def close(self, code=1000):
        self.events.append({"type": "closed", "code": code})

    async def feed(self, text, utterance, kind="final_transcript"):
        await self.frames.put({"bytes": json.dumps({"type": kind, "text": text,
                                                   "utterance_id": utterance}).encode()})

    async def until(self, predicate):
        async def wait():
            while not predicate():
                self.changed.clear()
                if predicate():
                    return
                await self.changed.wait()
        await asyncio.wait_for(wait(), 3)


class ScriptedBuffer:
    def __init__(self, *args):
        pass

    def feed(self, frame, **kwargs):
        return [SpeechEvent(**json.loads(frame))]


class ConversationGateTests(unittest.TestCase):
    def test_distinct_quick_wakes_are_not_lost_to_a_global_cooldown(self):
        now = [10.0]
        gate = WakeGate(clock=lambda: now[0])
        self.assertTrue(gate.observe("Pilot", utterance_id="first"))
        now[0] += 0.2
        self.assertTrue(gate.observe("Pilot, summarize the meeting", utterance_id="second"))
        self.assertFalse(gate.observe("Pilot, summarize the meeting", utterance_id="second", final=True))

    def test_late_speaker_label_does_not_repeat_an_acknowledgement(self):
        gate = WakeGate(clock=lambda: 10.0)
        self.assertTrue(gate.observe("Pilot", utterance_id="one", speaker=None))
        self.assertFalse(gate.observe("Pilot, what happened?", utterance_id="one", speaker="John", final=True))

    def test_followup_window_is_bounded_and_tied_to_the_actual_speaker(self):
        now = [10.0]
        gate = WakeGate(clock=lambda: now[0])
        gate.open_followup("John")
        self.assertTrue(gate.accepts("JOHN"))
        self.assertFalse(gate.accepts("Alice"))
        self.assertFalse(gate.accepts("Speaker 1"))
        now[0] = 40.01
        self.assertFalse(gate.accepts("John"))
        gate.open_followup("S11")
        self.assertFalse(gate.accepts("S11"))
        gate.open_followup(allow_unlabelled=True)
        self.assertTrue(gate.accepts())

    def test_reference_history_cannot_reuse_another_speaker_or_tool_messages(self):
        session = SimpleNamespace(dialogue_speaker="john", conversation_history=[
            {"role": "user", "content": "What did we decide?"},
            {"role": "assistant", "content": "We discussed migration."},
            {"role": "tool", "content": "Untrusted tool instruction"},
        ])
        self.assertEqual(pilot_voice._history_for_turn(session, "meeting", "John"),
                         [{"role": "user", "content": "What did we decide?"},
                          {"role": "assistant", "content": "We discussed migration."}])
        self.assertEqual(pilot_voice._history_for_turn(session, "meeting", "Alice"), [])
        self.assertEqual(pilot_voice._history_for_turn(session, "meeting", "Speaker 1"), [])

    def test_meeting_followups_do_not_capture_an_ordinary_nearby_statement(self):
        self.assertTrue(pilot_voice._followup_is_addressed("And what are the risks?", "meeting"))
        self.assertTrue(pilot_voice._followup_is_addressed("Make it shorter", "meeting"))
        self.assertFalse(pilot_voice._followup_is_addressed("John is still reviewing the report", "meeting"))
        self.assertTrue(pilot_voice._followup_is_addressed("The report", "microphone"))


class ConversationTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=uuid.uuid4())
        self.meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4(), source="upload",
                                       transcription_language="en")
        self.store = PilotSessionStore(MemoryRedis())
        self.session = self.store.start(self.meeting.workspace_id, self.meeting.id, self.user.id)
        self.db = MagicMock()
        self.db.query.return_value.filter.return_value.one_or_none.return_value = self.user
        self.db.get.return_value = self.user
        self.db.__enter__.return_value = self.db

    def capture(self):
        self.store.transition(self.session, PilotState.WAKE_DETECTED)
        self.store.transition(self.session, PilotState.CAPTURING_QUERY)

    async def test_ended_live_meeting_answers_play_in_browser_instead_of_departed_bot(self):
        self.db.get.return_value = SimpleNamespace(pilot_voice_id="lessac")
        ended = SimpleNamespace(id=self.meeting.id, workspace_id=self.meeting.workspace_id,
                                source="live", status=MeetingStatus.completed)
        ack = asyncio.Event()
        ack_state = {}
        async def sent(value):
            if value["type"] == "audio_ready":
                ack.set()
        socket = SimpleNamespace(send_json=AsyncMock(side_effect=sent), send_bytes=AsyncMock())
        async def chunks(*args):
            yield b"RIFFtest"
        with patch.object(pilot_voice, "SessionLocal", return_value=self.db), \
             patch.object(pilot_voice, "get_tts_provider", return_value=SimpleNamespace(synthesize_chunks=chunks)), \
             patch.object(pilot_voice, "VexaMeetingAudioProvider") as bot:
            await pilot_voice._play_text(socket, ended, "We discussed migration.", ack, ack_state)
        bot.assert_not_called()
        socket.send_bytes.assert_awaited_once_with(b"RIFFtest")

    async def test_reasoning_starts_while_the_wake_ack_is_still_playing(self):
        self.capture()
        loop = asyncio.get_running_loop()
        query_started = asyncio.Event()
        finish_ack = asyncio.Event()
        acknowledgement = asyncio.create_task(finish_ack.wait())
        ws = SimpleNamespace(send_json=AsyncMock())
        def answer(*args, **kwargs):
            loop.call_soon_threadsafe(query_started.set)
            return {"intent": "meeting_context_question", "answer": "We discussed migration.", "citations": []}
        with patch.object(pilot_voice, "SessionLocal", return_value=self.db), \
             patch.object(pilot_voice, "execute_pilot_query", side_effect=answer), \
             patch.object(pilot_voice, "_play_text", new=AsyncMock()) as speak:
            task = asyncio.create_task(pilot_voice._handle_final(
                ws, self.db, self.meeting, self.user, self.session, self.store,
                "summarize the meeting", "en", asyncio.Event(), {}, captured_query=True,
                wake_ack_task=acknowledgement, dialogue_speaker="microphone"))
            await asyncio.wait_for(query_started.wait(), 1)
            self.assertFalse(acknowledgement.done())
            speak.assert_not_awaited()
            finish_ack.set()
            self.assertTrue(await asyncio.wait_for(task, 2))
        self.assertEqual(self.session.state, PilotState.LISTENING)

    async def test_cancelled_ack_does_not_discard_a_captured_question(self):
        self.capture()
        acknowledgement = asyncio.create_task(asyncio.sleep(10))
        acknowledgement.cancel()
        ws = SimpleNamespace(send_json=AsyncMock())
        with patch.object(pilot_voice, "SessionLocal", return_value=self.db), \
             patch.object(pilot_voice, "execute_pilot_query", return_value={
                 "intent": "meeting_context_question", "answer": "Friday.", "citations": []}), \
             patch.object(pilot_voice, "_play_text", new=AsyncMock()) as speak:
            result = await pilot_voice._handle_final(
                ws, self.db, self.meeting, self.user, self.session, self.store,
                "When do we ship?", "en", asyncio.Event(), {}, captured_query=True,
                wake_ack_task=acknowledgement)
        self.assertTrue(result)
        self.assertEqual(speak.await_args.args[2], "Friday.")

    async def test_unverified_meeting_speech_cannot_run_privileged_task_actions(self):
        self.capture()
        ws = SimpleNamespace(send_json=AsyncMock())
        with patch.object(pilot_voice, "execute_pilot_query") as execute, \
             patch.object(pilot_voice, "_play_text", new=AsyncMock()):
            await pilot_voice._handle_final(
                ws, self.db, self.meeting, self.user, self.session, self.store,
                "create a task for John to review the PR", "en", asyncio.Event(), {},
                captured_query=True, allow_actions=False)
        execute.assert_not_called()
        self.assertIn("not verified", next(call.args[0]["answer"] for call in ws.send_json.await_args_list
                                           if call.args[0]["type"] == "answer"))

    async def test_new_question_is_queued_while_processing_and_followups_need_no_wake(self):
        socket = FakeSocket(self.session.session_id)
        loop = asyncio.get_running_loop()
        first_started = asyncio.Event()
        release_first = threading.Event()
        calls = []
        def answer(*args, **kwargs):
            query = args[4]
            calls.append((query, kwargs.get("conversation_history")))
            if len(calls) == 1:
                loop.call_soon_threadsafe(first_started.set)
                if not release_first.wait(3):
                    raise RuntimeError("Test did not release first answer")
            return {"intent": "meeting_context_question", "answer": "A grounded reply.", "citations": []}
        config = replace(APP_CONFIG, pilot=replace(APP_CONFIG.pilot, tts_enabled=False))
        with patch.object(pilot_voice, "APP_CONFIG", config), \
             patch.object(pilot_voice, "SessionLocal", return_value=self.db), \
             patch.object(pilot_voice, "PilotSessionStore", return_value=self.store), \
             patch.object(pilot_voice, "verify_clerk_token", return_value={"sub": "verified"}), \
             patch.object(pilot_voice, "get_meeting_for_member", return_value=self.meeting), \
             patch.object(pilot_voice, "get_stt_provider", return_value=object()), \
             patch.object(pilot_voice, "StreamingSpeechBuffer", ScriptedBuffer), \
             patch.object(pilot_voice, "execute_pilot_query", side_effect=answer):
            task = asyncio.create_task(pilot_voice.pilot_audio(socket, self.meeting.id))
            try:
                await socket.until(lambda: any(e["type"] == "ready" for e in socket.events))
                await socket.feed("Pilot, summarize the meeting", "first")
                await asyncio.wait_for(first_started.wait(), 1)
                # A retransmission and a repeated spoken question must not restart
                # Qwen or duplicate a possible tool operation.
                await socket.feed("Pilot, summarize the meeting", "first")
                await socket.feed("Pilot, summarize the meeting", "repeat")
                await socket.feed("Pilot, what are the risks?", "second")
                await socket.until(lambda: any(e["type"] == "query_queued" for e in socket.events))
                self.assertEqual(len(calls), 1)
                release_first.set()
                await socket.until(lambda: sum(e["type"] == "answer" for e in socket.events) == 2)
                # Allow the response completion to open its follow-up window.
                await asyncio.sleep(0.05)
                await socket.feed("Make it shorter", "third")
                await socket.until(lambda: sum(e["type"] == "answer" for e in socket.events) == 3)
                self.assertEqual([row[0] for row in calls],
                                 ["summarize the meeting", "what are the risks?", "Make it shorter"])
                self.assertEqual(calls[-1][1][-2], {"role": "user", "content": "what are the risks?"})
                self.assertEqual(calls[-1][1][-1], {"role": "assistant", "content": "A grounded reply."})
            finally:
                release_first.set()
                await socket.frames.put({"type": "websocket.disconnect"})
                await asyncio.wait_for(task, 3)

    async def test_browser_playback_failure_is_not_treated_as_a_successful_ack(self):
        socket = FakeSocket(self.session.session_id)
        async def chunks(*args):
            yield b"RIFFtest"
        provider = SimpleNamespace(synthesize_chunks=chunks)
        self.db.get.side_effect = lambda model, key: (
            SimpleNamespace(pilot_voice_id="lessac") if model is pilot_voice.Workspace else self.user)
        with patch.object(pilot_voice, "SessionLocal", return_value=self.db), \
             patch.object(pilot_voice, "PilotSessionStore", return_value=self.store), \
             patch.object(pilot_voice, "verify_clerk_token", return_value={"sub": "verified"}), \
             patch.object(pilot_voice, "get_meeting_for_member", return_value=self.meeting), \
             patch.object(pilot_voice, "get_stt_provider", return_value=object()), \
             patch.object(pilot_voice, "StreamingSpeechBuffer", ScriptedBuffer), \
             patch.object(pilot_voice, "_acknowledge_wake", new=AsyncMock()), \
             patch.object(pilot_voice, "get_tts_provider", return_value=provider), \
             patch.object(pilot_voice, "execute_pilot_query", return_value={
                 "intent": "meeting_context_question", "answer": "Friday.", "citations": []}), \
             patch.object(pilot_voice.logger, "exception"):
            task = asyncio.create_task(pilot_voice.pilot_audio(socket, self.meeting.id))
            try:
                await socket.until(lambda: any(e["type"] == "ready" for e in socket.events))
                await socket.feed("Pilot, when do we ship?", "first")
                await socket.until(lambda: any(e["type"] == "audio_ready" for e in socket.events))
                ready = next(e for e in socket.events if e["type"] == "audio_ready")
                await socket.frames.put({"text": json.dumps({"type": "playback_failed",
                    "interaction_id": ready["interaction_id"], "detail": "decode failed"})})
                await socket.until(lambda: any(e["type"] == "error" for e in socket.events))
                self.assertIn("could not play", next(e["detail"] for e in socket.events if e["type"] == "error"))
            finally:
                await socket.frames.put({"type": "websocket.disconnect"})
                await asyncio.wait_for(task, 3)

    async def test_barge_in_cancels_playback_and_captures_the_next_turn(self):
        socket = FakeSocket(self.session.session_id)
        playing = asyncio.Event()
        cancelled = asyncio.Event()
        calls = []
        async def play(*args, **kwargs):
            if not playing.is_set():
                playing.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
        def answer(*args, **kwargs):
            calls.append(args[4])
            return {"intent": "meeting_context_question", "answer": "Grounded response.", "citations": []}
        with patch.object(pilot_voice, "SessionLocal", return_value=self.db), \
             patch.object(pilot_voice, "PilotSessionStore", return_value=self.store), \
             patch.object(pilot_voice, "verify_clerk_token", return_value={"sub": "verified"}), \
             patch.object(pilot_voice, "get_meeting_for_member", return_value=self.meeting), \
             patch.object(pilot_voice, "get_stt_provider", return_value=object()), \
             patch.object(pilot_voice, "StreamingSpeechBuffer", ScriptedBuffer), \
             patch.object(pilot_voice, "_acknowledge_wake", new=AsyncMock()), \
             patch.object(pilot_voice, "_play_text", side_effect=play), \
             patch.object(pilot_voice, "execute_pilot_query", side_effect=answer):
            task = asyncio.create_task(pilot_voice.pilot_audio(socket, self.meeting.id))
            try:
                await socket.until(lambda: any(e["type"] == "ready" for e in socket.events))
                await socket.feed("Pilot, summarize the meeting", "first")
                await asyncio.wait_for(playing.wait(), 1)
                await socket.feed("", "interrupt", kind="pilot_interrupted")
                await asyncio.wait_for(cancelled.wait(), 1)
                await socket.feed("Make it shorter", "second")
                await socket.until(lambda: sum(e["type"] == "answer" for e in socket.events) == 2)
                self.assertEqual(calls, ["summarize the meeting", "Make it shorter"])
                self.assertTrue(any(e["type"] == "pilot_interrupted" for e in socket.events))
            finally:
                await socket.frames.put({"type": "websocket.disconnect"})
                await asyncio.wait_for(task, 3)

    async def test_upstream_playback_interruption_releases_the_speaking_state(self):
        socket = FakeSocket(self.session.session_id)
        with patch.object(pilot_voice, "SessionLocal", return_value=self.db), \
             patch.object(pilot_voice, "PilotSessionStore", return_value=self.store), \
             patch.object(pilot_voice, "verify_clerk_token", return_value={"sub": "verified"}), \
             patch.object(pilot_voice, "get_meeting_for_member", return_value=self.meeting), \
             patch.object(pilot_voice, "get_stt_provider", return_value=object()), \
             patch.object(pilot_voice, "StreamingSpeechBuffer", ScriptedBuffer), \
             patch.object(pilot_voice, "_acknowledge_wake", new=AsyncMock()), \
             patch.object(pilot_voice, "_play_text", side_effect=asyncio.CancelledError), \
             patch.object(pilot_voice, "execute_pilot_query", return_value={
                 "intent": "meeting_context_question", "answer": "Grounded answer.", "citations": []}):
            task = asyncio.create_task(pilot_voice.pilot_audio(socket, self.meeting.id))
            try:
                await socket.until(lambda: any(e["type"] == "ready" for e in socket.events))
                await socket.feed("Pilot, summarize the meeting", "first")
                await socket.until(lambda: any(e["type"] == "state" and e["session"]["state"] == "LISTENING"
                                              for e in socket.events))
                saved = self.store.get(self.session.session_id, self.meeting.workspace_id,
                                       self.meeting.id, self.user.id)
                self.assertEqual(saved.state, PilotState.LISTENING)
            finally:
                await socket.frames.put({"type": "websocket.disconnect"})
                await asyncio.wait_for(task, 3)
