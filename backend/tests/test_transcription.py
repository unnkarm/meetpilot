import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from app.core.app_config import APP_CONFIG
from app.services.transcription import transcribe_audio


class TranscriptionTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("meeting.wav")
        self.segment = {"speaker": "Speaker 1", "start_time": 0.0, "end_time": 2.0,
                        "text": "Actual speech recognized by Whisper."}

    @patch("app.services.transcription._transcribe_local_audio")
    def test_default_uses_local_provider(self, local):
        local.return_value = [self.segment]
        self.assertEqual(transcribe_audio(self.path), [self.segment])
        local.assert_called_once_with(self.path, None)

    @patch("app.services.transcription._transcribe_hf_space")
    def test_provider_switch_uses_selected_adapter(self, remote):
        remote.return_value = [self.segment]
        changed = replace(APP_CONFIG, transcription=replace(APP_CONFIG.transcription, provider="huggingface"))
        with patch("app.services.transcription.APP_CONFIG", changed):
            self.assertEqual(transcribe_audio(self.path), [self.segment])
        remote.assert_called_once()

    @patch("app.services.transcription._transcribe_local_audio")
    def test_failure_never_invents_transcript(self, local):
        local.return_value = []
        with self.assertRaisesRegex(RuntimeError, "no speech"):
            transcribe_audio(self.path)
