"""Responsive wakes, bounded follow-ups, and workspace voice authorization."""
import asyncio
import io
import unittest
import uuid
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.deps import get_current_user
from app.api.routes.pilot_settings import router
from app.api.routes.pilot_voice import _acknowledge_wake
from app.database.session import get_db
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.services.pilot_tts import parse_voice_token, _wav
from app.services.pilot_wakeword import TranscriptPhraseWakeWord, WakeGate
from app.workers.vexa_meeting import voice_event


class WakeTests(unittest.TestCase):
    def test_name_aliases_are_responsive_on_first_partial(self):
        provider = TranscriptPhraseWakeWord()
        for phrase in ("Pilot", "Hey Pilot", "Hey, pilot!", "MeetPilot", "okay meet pilot", "Hi Pilot", "Hello Pilot", "can you help, Pilot"):
            self.assertEqual(provider.detect(phrase), "")
            self.assertTrue(WakeGate(clock=lambda: 10).observe(phrase, final=False, utterance_id="1"))
        self.assertEqual(provider.detect("Pilot, what did we decide?"), "what did we decide?")
        self.assertIsNone(provider.detect("pilotage"))

    def test_partial_final_retransmissions_do_not_repeat_ack(self):
        now = [10.0]
        gate = WakeGate(clock=lambda: now[0])
        self.assertTrue(gate.observe("Pilot", utterance_id="turn-1", speaker="John"))
        now[0] = 14.0
        self.assertFalse(gate.observe("Pilot, tell me", final=True, utterance_id="turn-1", speaker="John"))
        self.assertTrue(gate.observe("Pilot", utterance_id="turn-2", speaker="John"))

    def test_followup_expires_and_rejects_another_speaker(self):
        now = [10.0]
        gate = WakeGate(clock=lambda: now[0])
        gate.observe("Hey Pilot", speaker="John")
        self.assertTrue(gate.accepts("John"))
        self.assertFalse(gate.accepts("Alice"))
        now[0] = 21.0
        self.assertFalse(gate.accepts("John"))

    def test_wake_ack_does_not_call_the_llm(self):
        ws = SimpleNamespace(send_json=AsyncMock())
        meeting = SimpleNamespace(id=uuid.uuid4())
        with patch("app.api.routes.pilot_voice._play_text", new=AsyncMock()) as play, \
             patch("app.api.routes.pilot_voice.execute_pilot_query") as query:
            asyncio.run(_acknowledge_wake(ws, meeting, asyncio.Event(), {}))
        ws.send_json.assert_awaited_once_with({"type": "wake_acknowledged", "text": "Yes sir."})
        self.assertEqual(play.await_args.args[2], "Yes sir.")
        query.assert_not_called()

    def test_voice_correlation_preserves_selected_voice(self):
        self.assertEqual(parse_voice_token("mp/ryan/" + uuid.uuid4().hex), "ryan")
        self.assertEqual(parse_voice_token(uuid.uuid4().hex), "lessac")
        with self.assertRaises(ValueError): parse_voice_token("mp/../../secret")

    def test_partial_and_final_share_the_source_id(self):
        row = {"segment_id": "source-1", "text": "Pilot", "speaker": "John"}
        self.assertEqual(voice_event(row, "partial_transcript")["utterance_id"],
                         voice_event(row, "final_transcript")["utterance_id"])


class VoiceSettingsTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.ident = uuid.uuid4()
        self.user = SimpleNamespace(id=uuid.uuid4())
        self.workspace = SimpleNamespace(pilot_voice_id="lessac")
        self.member = SimpleNamespace(role=WorkspaceRole.owner)
        self.db = MagicMock()
        self.db.get.side_effect = lambda model, key, **kwargs: (
            self.member if model is WorkspaceMember and key == (self.ident, self.user.id) else
            self.workspace if model is Workspace and key == self.ident else None)
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(self.app)
        self.path = f"/api/v1/workspaces/{self.ident}/pilot"

    def test_other_workspace_cannot_read_change_or_preview(self):
        path = f"/api/v1/workspaces/{uuid.uuid4()}/pilot"
        self.assertEqual(self.client.get(path + "/settings").status_code, 403)
        self.assertEqual(self.client.patch(path + "/settings", json={"voice_id": "ryan"}).status_code, 403)
        self.assertEqual(self.client.post(path + "/voice-preview", json={"voice_id": "ryan"}).status_code, 403)
        self.db.commit.assert_not_called()

    def test_member_can_preview_but_not_change(self):
        self.member.role = WorkspaceRole.member
        response = self.client.get(self.path + "/settings")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["can_edit"])
        self.assertEqual(self.client.patch(self.path + "/settings", json={"voice_id": "ryan"}).status_code, 403)

    def test_owner_saves_voice_and_warms_ack(self):
        with patch("app.api.routes.pilot_settings.require_voice", return_value="ryan"), \
             patch("app.api.routes.pilot_settings.synthesize_wake_ack", new=AsyncMock()) as warm:
            response = self.client.patch(self.path + "/settings", json={"voice_id": "ryan"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.workspace.pilot_voice_id, "ryan")
        self.db.commit.assert_called_once()
        warm.assert_awaited_once_with("ryan")

    def test_unknown_voice_is_rejected_without_save(self):
        response = self.client.patch(self.path + "/settings", json={"voice_id": "../../etc/passwd"})
        self.assertEqual(response.status_code, 422)
        self.db.commit.assert_not_called()

    def test_preview_is_valid_wav_and_does_not_change_voice(self):
        provider = SimpleNamespace(synthesize=AsyncMock(return_value=_wav(b'\0\0' * 1600, 16000)))
        with patch("app.api.routes.pilot_settings.require_voice", return_value="ryan"), \
             patch("app.api.routes.pilot_settings.get_tts_provider", return_value=provider):
            response = self.client.post(self.path + "/voice-preview", json={"voice_id": "ryan"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        with wave.open(io.BytesIO(response.content)) as wav:
            self.assertEqual(wav.getnframes(), 1600)
        self.assertEqual(self.workspace.pilot_voice_id, "lessac")
        self.db.commit.assert_not_called()
