"""Real Redis -> authenticated WebSocket voice transport and barge-in checks."""
import asyncio
import base64
import json
import os
import struct
import threading
import time
import unittest
import uuid
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import redis
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.routes.pilot_voice import router
from app.core.config import settings
from app.services.pilot_session import PilotSessionStore
from app.services.pilot_tts import _wav
from app.models.workspace import Workspace
from app.models.meeting import MeetingStatus


class MemoryRedis:
    def __init__(self): self.rows = {}
    def setex(self, key, ttl, value): self.rows[key] = value
    def get(self, key): return self.rows.get(key)


class FakeTTS:
    async def synthesize_chunks(self, *args):
        yield _wav(struct.pack('<h', 1000) * 1600, 16000)


@unittest.skipUnless(os.getenv("MEETPILOT_RUN_PILOT_INTEGRATION") == "1", "Requires local Redis")
class BotVoiceTransportTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.meeting = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4(), source="live", status=MeetingStatus.in_progress)
        self.user = SimpleNamespace(id=uuid.uuid4())
        self.store = PilotSessionStore(MemoryRedis())
        self.session = self.store.start(self.meeting.workspace_id, self.meeting.id, self.user.id)
        self.db = MagicMock()
        self.db.query().filter().one_or_none.return_value = self.user
        self.db.__enter__.return_value = self.db
        self.db.get.side_effect = lambda model, ident: SimpleNamespace(pilot_voice_id="lessac") if model is Workspace else self.user
        self.redis = redis.Redis.from_url(settings.REDIS_URL)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("app.api.routes.pilot_voice.SessionLocal", return_value=self.db))
        self.stack.enter_context(patch("app.api.routes.pilot_voice.verify_clerk_token", return_value={"sub": "test-user"}))
        self.access = self.stack.enter_context(patch("app.api.routes.pilot_voice.get_meeting_for_member", return_value=self.meeting))
        self.stack.enter_context(patch("app.api.routes.pilot_voice.PilotSessionStore", return_value=self.store))

    def publish(self, data, channel="pcm"):
        return self.redis.publish(f"native-meeting:{self.meeting.id}:{channel}", json.dumps(data))

    def speak(self, text="Hey Pilot, what did we decide?"):
        deadline = time.monotonic() + 3
        channel = f"native-meeting:{self.meeting.id}:transcript"
        while not self.redis.pubsub_numsub(channel)[0][1]:
            if time.monotonic() >= deadline: self.fail("Vexa transcript subscription did not start")
            time.sleep(0.01)
        self.publish({"type": "final_transcript", "text": text, "speaker": "Remote guest", "language": "en"}, "transcript")

    def test_remote_voice_routes_answer_and_barge_in_cancels_playback(self):
        transcriber = MagicMock()
        transcriber.transcribe.side_effect = [("Hey Pilot, what did we decide?", "en"), ("What about the budget?", "en")]
        query = self.stack.enter_context(patch("app.api.routes.pilot_voice.execute_pilot_query", side_effect=[
            {"intent": "meeting_context_question", "answer": "Use PostgreSQL.", "citations": []},
            {"intent": "meeting_context_question", "answer": "", "citations": []},
        ]))
        self.stack.enter_context(patch("app.api.routes.pilot_voice.get_stt_provider", return_value=transcriber))
        self.stack.enter_context(patch("app.api.routes.pilot_voice.get_tts_provider", return_value=FakeTTS()))
        playing = threading.Event()
        async def playback(text, *args, **kwargs):
            if text == "Yes sir.":
                return
            playing.set()
            await asyncio.sleep(30)
        from app.services.vexa_audio_provider import VexaMeetingAudioProvider
        output = VexaMeetingAudioProvider(self.meeting.id, self.meeting.workspace_id)
        output.speak_text = AsyncMock(side_effect=playback)
        output.interrupt = AsyncMock()
        self.stack.enter_context(patch("app.api.routes.pilot_voice.VexaMeetingAudioProvider", return_value=output))

        with TestClient(self.app) as client, client.websocket_connect(f"/api/v1/meetings/{self.meeting.id}/pilot/audio") as ws:
            ws.send_json({"token": "test-token", "session_id": self.session.session_id, "input_source": "meeting"})
            self.assertEqual(ws.receive_json()["type"], "ready")
            self.speak()
            while ws.receive_json()["type"] != "answer": pass
            self.assertTrue(playing.wait(3))
            self.publish({"type": "partial_transcript", "text": "What about", "speaker": "Remote guest"}, "transcript")
            while True:
                event = ws.receive_json()
                if event["type"] == "pilot_interrupted": break
            self.assertEqual(event["session"]["state"], "CAPTURING_QUERY")
            self.speak("What about the budget?")
            while True:
                event = ws.receive_json()
                if event["type"] == "answer": break
            self.assertEqual(query.call_count, 2)
            self.assertEqual(query.call_args.args[4], "What about the budget?")
            output.interrupt.assert_awaited()
        self.redis.close()

    def test_partial_name_gets_one_ack_and_final_query_is_not_lost(self):
        query = self.stack.enter_context(patch("app.api.routes.pilot_voice.execute_pilot_query",
            return_value={"intent": "meeting_context_question", "answer": "", "citations": []}))
        output = MagicMock()
        output.speak_text = AsyncMock()
        self.stack.enter_context(patch("app.api.routes.pilot_voice.VexaMeetingAudioProvider", return_value=output))
        self.stack.enter_context(patch("app.api.routes.pilot_voice.get_stt_provider"))
        with TestClient(self.app) as client, client.websocket_connect(f"/api/v1/meetings/{self.meeting.id}/pilot/audio") as ws:
            ws.send_json({"token": "test-token", "session_id": self.session.session_id, "input_source": "meeting"})
            self.assertEqual(ws.receive_json()["type"], "ready")
            deadline = time.monotonic() + 3
            while not self.redis.pubsub_numsub(f"native-meeting:{self.meeting.id}:transcript")[0][1]:
                if time.monotonic() > deadline: self.fail("subscription missing")
                time.sleep(0.01)
            utterance = {"speaker": "Remote guest", "utterance_id": "wake-1"}
            self.publish({**utterance, "type": "partial_transcript", "text": "Pilot"}, "transcript")
            while True:
                event = ws.receive_json()
                if event["type"] == "wake_acknowledged": break
            self.assertEqual(event["text"], "Yes sir.")
            query.assert_not_called()
            self.publish({**utterance, "type": "partial_transcript", "text": "Pilot, what did we decide?"}, "transcript")
            self.publish({**utterance, "type": "final_transcript", "text": "Pilot, what did we decide?"}, "transcript")
            while ws.receive_json()["type"] != "answer": pass
            self.assertEqual(query.call_args.args[4], "what did we decide?")
            output.speak_text.assert_awaited_once_with("Yes sir.", "lessac", language=None)
        self.redis.close()

    def test_foreign_member_cannot_subscribe_to_bot_audio(self):
        self.access.side_effect = HTTPException(status_code=403, detail="Not a workspace member")
        with TestClient(self.app) as client, client.websocket_connect(f"/api/v1/meetings/{self.meeting.id}/pilot/audio") as ws:
            ws.send_json({"token": "test-token", "session_id": self.session.session_id, "input_source": "meeting"})
            with self.assertRaises(WebSocketDisconnect) as denied:
                ws.receive_json()
            self.assertEqual(denied.exception.code, 1008)
