import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Provide dummy mocks if optional dependencies are not in host environment
try:
    import pydantic_settings
except ImportError:
    from unittest.mock import MagicMock
    sys.modules["pydantic_settings"] = MagicMock()

try:
    import google.genai
    import google.genai.errors
except ImportError:
    from unittest.mock import MagicMock
    sys.modules["google"] = MagicMock()
    sys.modules["google.genai"] = MagicMock()
    sys.modules["google.genai.errors"] = MagicMock()

try:
    import redis
except ImportError:
    from unittest.mock import MagicMock
    sys.modules["redis"] = MagicMock()

try:
    import gradio_client
except ImportError:
    from unittest.mock import MagicMock
    sys.modules["gradio_client"] = MagicMock()

import unittest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.transcription import (
    TranscriptSegmentDict,
    _transcribe_hf_space,
    transcribe_audio,
)


class TestTranscriptionService(unittest.TestCase):
    def setUp(self):
        self.sample_audio_path = Path("backend/tests/sample_meeting.wav")

    @patch("app.services.transcription.split_audio")
    @patch("app.services.transcription.cleanup_temp_chunks")
    def test_hf_space_successful_transcription(self, mock_cleanup, mock_split):
        """Tests successful transcription response from Hugging Face ZeroGPU Gradio Space (100% mocked)."""
        mock_split.return_value = [
            {"path": self.sample_audio_path, "start_offset_ms": 0, "duration_ms": 5000, "is_temp": False}
        ]

        mock_client = MagicMock()
        mock_client.predict.return_value = {
            "segments": [
                {"speaker": "Speaker 1", "start_time": 0.0, "end_time": 2.5, "text": "Welcome to the sync."},
                {"speaker": "Speaker 2", "start_time": 2.8, "end_time": 5.0, "text": "Thanks, glad to be here."},
            ],
            "language": "en",
            "duration": 5.0,
        }

        mock_client_cls = MagicMock(return_value=mock_client)
        mock_handle_file = MagicMock(side_effect=lambda x: f"handled_{x}")

        with patch.dict(sys.modules, {"gradio_client": MagicMock(Client=mock_client_cls, handle_file=mock_handle_file)}):
            with patch.object(settings, "HF_SPACE_ID", "Subham05x/meetpilot-whisper-diarization"):
                with patch.object(settings, "HF_API_TOKEN", "hf_test_token_123"):
                    segments = _transcribe_hf_space(self.sample_audio_path, meeting_id="test-meet-1")

        # Verify Client initialization and predict invocation
        mock_client_cls.assert_called_once_with(
            "Subham05x/meetpilot-whisper-diarization",
            token="hf_test_token_123",
        )
        mock_client.predict.assert_called_once_with(
            audio_file=f"handled_{str(self.sample_audio_path)}",
            min_speakers=None,
            max_speakers=None,
            language=None,
            api_name="/transcribe",
        )

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["speaker"], "Speaker 1")
        self.assertEqual(segments[0]["start_time"], 0.0)
        self.assertEqual(segments[0]["end_time"], 2.5)
        self.assertEqual(segments[0]["text"], "Welcome to the sync.")

        self.assertEqual(segments[1]["speaker"], "Speaker 2")
        self.assertEqual(segments[1]["start_time"], 2.8)
        self.assertEqual(segments[1]["end_time"], 5.0)
        self.assertEqual(segments[1]["text"], "Thanks, glad to be here.")

    @patch("app.services.transcription._transcribe_hf_space")
    @patch("app.services.transcription._transcribe_gemini")
    def test_hf_space_fallback_to_gemini_on_error(self, mock_gemini, mock_hf_space):
        """Tests that when the HF Space throws an error or times out, transcribe_audio falls back to Gemini without retrying."""
        mock_hf_space.side_effect = RuntimeError("ZeroGPU Space GPU timeout / queue full")
        mock_gemini.return_value = [
            TranscriptSegmentDict(
                speaker="Speaker 1",
                start_time=0.0,
                end_time=3.0,
                text="Recovered transcript via Gemini fallback.",
            )
        ]

        with patch.object(settings, "HF_SPACE_ID", "Subham05x/meetpilot-whisper-diarization"):
            with patch.object(settings, "HF_API_TOKEN", "hf_test_token_123"):
                with patch.object(settings, "GEMINI_API_KEY", "gemini_test_key"):
                    result = transcribe_audio(self.sample_audio_path, meeting_id="test-meet-fallback")

        mock_hf_space.assert_called_once()
        mock_gemini.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Recovered transcript via Gemini fallback.")

    @patch("app.services.transcription._transcribe_hf_space")
    @patch("app.services.transcription._transcribe_gemini")
    @patch("app.services.transcription._transcribe_local_audio")
    def test_gemini_fallback_to_local_when_all_fail(self, mock_local, mock_gemini, mock_hf_space):
        """Tests that local audio parser fallback triggers if both HF Space and Gemini are unavailable."""
        mock_hf_space.side_effect = Exception("HF Space unreachable")
        mock_gemini.side_effect = Exception("Gemini quota 429")
        mock_local.return_value = [
            TranscriptSegmentDict(
                speaker="Speaker 1",
                start_time=0.0,
                end_time=5.0,
                text="Local speech parser fallback segment.",
            )
        ]

        with patch.object(settings, "HF_SPACE_ID", "Subham05x/meetpilot-whisper-diarization"):
            with patch.object(settings, "HF_API_TOKEN", "hf_test_token_123"):
                with patch.object(settings, "GEMINI_API_KEY", "gemini_test_key"):
                    result = transcribe_audio(self.sample_audio_path, meeting_id="test-meet-local")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Local speech parser fallback segment.")


if __name__ == "__main__":
    unittest.main()
