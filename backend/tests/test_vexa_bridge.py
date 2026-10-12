"""Vexa protocol, tenant isolation, timestamp and local audio auth regressions."""
import io
import json
import unittest
import uuid
from unittest.mock import patch
import httpx

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.vexa_audio import router
from app.core.config import settings
from app.services.vexa_client import VexaClient, VexaError
from app.workers.vexa_meeting import confirmed_segments, segment_times, voice_event


class VexaBridgeTests(unittest.TestCase):
    def test_voice_ids_handle_absolute_and_missing_timestamp_fields(self):
        pending = {"absolute_start_time": "2026-10-08T10:00:01.123Z", "text": "Pilot"}
        confirmed = {**pending, "speaker": "John", "text": "Pilot, summarize the meeting"}
        self.assertEqual(voice_event(pending, "partial_transcript")["utterance_id"],
                         voice_event(confirmed, "final_transcript")["utterance_id"])
        later = {**confirmed, "absolute_start_time": "2026-10-08T10:00:02.123Z"}
        self.assertNotEqual(voice_event(confirmed, "final_transcript")["utterance_id"],
                            voice_event(later, "final_transcript")["utterance_id"])
        self.assertIsNone(voice_event({"speaker": "John", "text": "Pilot"}, "partial_transcript")["utterance_id"])
        self.assertEqual(voice_event({"start": 0, "text": "Pilot"}, "partial_transcript")["utterance_id"], "time:0")

    def test_pending_is_not_evidence_and_bundle_preserves_speakers(self):
        payload = {"type": "transcript", "speaker": "Alice", "confirmed": [
            {"segment_id": "1", "completed": True, "text": "Agreed."}],
            "pending": [{"text": "Maybe we should..."}]}
        rows = confirmed_segments(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["speaker"], "Alice")
        self.assertEqual(confirmed_segments({"type": "transcription_segment", "text": "Guess"}), [])

    def test_epoch_iso_and_relative_timestamps_agree(self):
        epoch = 1791300000
        self.assertEqual(segment_times({"start": epoch + 5, "end": epoch + 8}, epoch), (5, 8))
        self.assertEqual(segment_times({"start": 5, "end": 8}, epoch), (5, 8))
        self.assertEqual(segment_times({"absolute_start_time": "2026-10-06T15:20:05Z",
                                        "absolute_end_time": "2026-10-06T15:20:08Z"}, epoch), (5, 8))
        self.assertIsNone(segment_times({"text": "missing evidence"}, epoch))

    def test_foreign_workspace_binding_cannot_control_bot(self):
        workspace = uuid.uuid4()
        with patch("app.services.vexa_client.redis.Redis.from_url") as factory:
            factory.return_value.get.return_value = json.dumps({"workspace_id": str(uuid.uuid4()), "provider_id": 1})
            with self.assertRaises(VexaError):
                VexaClient(workspace).command(uuid.uuid4(), {"action": "speak_stop"})

    def test_audio_endpoint_requires_its_private_service_token(self):
        app = FastAPI()
        app.include_router(router)
        with patch.object(settings, "VEXA_STT_TOKEN", "private-test-key"), TestClient(app) as client:
            response = client.post("/internal/vexa/v1/audio/transcriptions", files={"file": ("audio.wav", b"invalid")})
            self.assertEqual(response.status_code, 401)
            response = client.post("/internal/vexa/v1/audio/transcriptions", files={"file": ("audio.wav", b"invalid")},
                                   headers={"Authorization": "Bearer private-test-key"})
            self.assertEqual(response.status_code, 422)
            response = client.post("/internal/vexa/v1/audio/speech", json={"input": "Speak"})
            self.assertEqual(response.status_code, 401)

    def test_vexa_spawn_leaves_platform_parsing_to_upstream(self):
        with patch("app.services.vexa_client.redis.Redis.from_url"), patch.object(VexaClient, "request", return_value={}) as request:
            VexaClient(uuid.uuid4()).start("https://zoom.us/j/123456789?pwd=example", "MeetPilot")
            body = request.call_args.kwargs["json"]
            self.assertIn("pwd=example", body["meeting_url"])
            self.assertNotIn("native_meeting_id", body)
            self.assertTrue(body["transcribe_enabled"])

    def test_transient_gateway_failure_is_retried_for_reads(self):
        unavailable = httpx.Response(503, request=httpx.Request("GET", "http://vexa/meetings/1"))
        recovered = httpx.Response(200, json={"id": 1, "status": "active"},
                                   request=httpx.Request("GET", "http://vexa/meetings/1"))
        with patch("app.services.vexa_client.redis.Redis.from_url"), patch.object(VexaClient, "api_key", return_value="private"), \
             patch("app.services.vexa_client.httpx.request", side_effect=[unavailable, recovered]) as request, \
             patch("app.services.vexa_client.time.sleep"):
            self.assertEqual(VexaClient(uuid.uuid4()).meeting(1)["status"], "active")
            self.assertEqual(request.call_count, 2)

    def test_spawn_is_not_repeated_on_ambiguous_gateway_failure(self):
        unavailable = httpx.Response(503, request=httpx.Request("POST", "http://vexa/bots"))
        with patch("app.services.vexa_client.redis.Redis.from_url"), patch.object(VexaClient, "api_key", return_value="private"), \
             patch("app.services.vexa_client.httpx.request", return_value=unavailable) as request:
            with self.assertRaises(VexaError):
                VexaClient(uuid.uuid4()).start("https://meet.google.com/abc-defg-hij", "MeetPilot")
            self.assertEqual(request.call_count, 1)
