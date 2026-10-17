"""Per-meeting hints and display preferences; no ASR model or service startup."""
import io
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from app.schemas.meeting import LiveMeetingStartRequest
from app.services.meeting_language import recognition_hint, display_script
from app.services.pilot_streaming_stt import LocalWhisperSTT, MeetingLanguageSTT
from app.services.transcription import TranscriptionResult, transcribe_audio_with_metadata, _transcribe_local_audio
from app.services.vexa_client import VexaClient


class MeetingLanguageTests(unittest.TestCase):
    def test_new_live_meetings_default_to_english(self):
        payload = LiveMeetingStartRequest(workspace_id=uuid.uuid4(), meeting_url="https://meet.google.com/abc-defg-hij")
        self.assertEqual(payload.transcription_language, "en")
        self.assertEqual(display_script(payload.transcription_language, payload.display_script), "original")

    def test_hindi_bengali_and_explicit_original_display(self):
        for language in ("hi", "bn"):
            self.assertEqual(display_script(language), "romanized")
            self.assertEqual(display_script(language, "original"), "original")
            self.assertEqual(recognition_hint(language), language)
        self.assertIsNone(recognition_hint("auto"))
        self.assertIsNone(recognition_hint(None))
        with self.assertRaises(ValueError): display_script("ta", "romanized")

    def test_unknown_language_cannot_reach_the_bot(self):
        with self.assertRaises(ValidationError):
            LiveMeetingStartRequest(workspace_id=uuid.uuid4(), meeting_url="https://meet.google.com/abc-defg-hij", transcription_language="xx")
        with self.assertRaises(ValueError): recognition_hint("xx")

    def test_selected_bengali_reaches_vexa_spawn_without_external_asr(self):
        with patch("app.services.vexa_client.redis.Redis.from_url"), patch.object(VexaClient, "request", return_value={}) as request:
            vexa = VexaClient(uuid.uuid4())
            vexa.start("https://meet.google.com/abc-defg-hij", "Pilot", "bn")
            self.assertEqual(request.call_args.kwargs["json"]["language"], "bn")
            vexa.start("https://meet.google.com/abc-defg-hij", "Pilot", "auto")
            self.assertIsNone(request.call_args.kwargs["json"]["language"])

    def test_microphone_hints_share_one_model_and_preserve_original_text(self):
        provider = LocalWhisperSTT()
        provider.model = MagicMock()
        provider.model.transcribe.return_value = ([SimpleNamespace(text="আমরা API deploy করব।")], SimpleNamespace(language="bn"))
        bengali = MeetingLanguageSTT(provider, "bn")
        text, language = bengali.transcribe(b"\0\0" * 160)
        self.assertEqual(text, "আমরা API deploy করব।")
        self.assertEqual(language, "bn")
        self.assertEqual(provider.model.transcribe.call_args.kwargs["language"], "bn")
        english = MeetingLanguageSTT(provider, "en")
        english.transcribe(b"\0\0" * 160)
        self.assertIs(bengali.provider, english.provider)
        self.assertEqual(provider.model.transcribe.call_args.kwargs["language"], "en")

    def test_upload_selection_overrides_global_auto_without_changing_evidence(self):
        model = MagicMock()
        model.transcribe.return_value = ([SimpleNamespace(text="আমি API update করব।", start=0.0, end=3.0)],
                                         SimpleNamespace(language="bn", language_probability=0.95))
        with patch.dict("sys.modules", {"faster_whisper": SimpleNamespace(WhisperModel=MagicMock(return_value=model))}), \
             patch("app.services.transcription.split_audio", return_value=[{"path": Path("chunk.wav"), "start_offset_ms": 0}]), \
             patch("app.services.transcription.cleanup_temp_chunks"):
            result = _transcribe_local_audio(Path("meeting.wav"), "bn")
        self.assertEqual(model.transcribe.call_args.kwargs["language"], "bn")
        self.assertEqual(model.transcribe.call_args.kwargs["task"], "transcribe")
        self.assertEqual(result.segments[0]["text"], "আমি API update করব।")

    def test_provider_wrapper_retains_each_meetings_hint(self):
        provider = MagicMock()
        source = "আমি API update করব।"
        provider.transcribe.return_value = TranscriptionResult([{"speaker": "Alice", "start_time": 0, "end_time": 3, "text": source, "language_code": "bn"}], language_code="bn")
        with patch("app.services.transcription.get_transcription_provider", return_value=provider):
            result = transcribe_audio_with_metadata(Path("meeting.wav"), "owned-id", "bn")
        self.assertEqual(provider.language_hint, "bn")
        self.assertEqual(result.segments[0]["text"], source)
