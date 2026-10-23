"""Capture regressions using deterministic PCM; no Whisper model or server."""

import struct
import unittest

from app.services.pilot_streaming_stt import StreamingSpeechBuffer


class RecordingSTT:
    def __init__(self):
        self.frames = []

    def transcribe(self, pcm):
        self.frames.append(pcm)
        return "Pilot, summarize our meeting", "en"


class StreamingCaptureTests(unittest.TestCase):
    def test_keeps_quiet_leading_audio_and_all_final_frames(self):
        stt = RecordingSTT()
        buffer = StreamingSpeechBuffer(stt)
        quiet = struct.pack("<h", 100) * 1600
        voiced = struct.pack("<h", 5000) * 1600
        silence = b"\0\0" * 1600
        for _ in range(4):
            self.assertEqual(buffer.feed(quiet), [])
        buffer.feed(voiced)
        events = []
        for _ in range(7):
            events += buffer.feed(silence)
        self.assertEqual(stt.frames[-1], quiet * 2 + voiced + silence * 7)
        self.assertEqual([event.type for event in events], ["speech_ended", "language_detected", "final_transcript"])

    def test_first_partial_arrives_early_and_shares_one_utterance_id(self):
        buffer = StreamingSpeechBuffer(RecordingSTT())
        voiced = struct.pack("<h", 5000) * 1600
        events = []
        for _ in range(6):
            events += buffer.feed(voiced)
        self.assertEqual([event.type for event in events], ["speech_started", "partial_transcript"])
        events += buffer.flush()
        ids = {event.utterance_id for event in events}
        self.assertEqual(len(ids), 1)
        self.assertNotIn(None, ids)
        next_start = buffer.feed(voiced)[0]
        self.assertNotIn(next_start.utterance_id, ids)

    def test_question_longer_than_fifteen_seconds_is_not_cut_mid_sentence(self):
        buffer = StreamingSpeechBuffer(RecordingSTT())
        voiced = struct.pack("<h", 5000) * 16000
        events = []
        for _ in range(16):
            events += buffer.feed(voiced)
        self.assertNotIn("final_transcript", [event.type for event in events])
        self.assertTrue(buffer.speaking)
        self.assertEqual(len(buffer.frames), len(voiced) * 16)
        self.assertIn("final_transcript", [event.type for event in buffer.flush()])

    def test_assistant_audio_never_enters_pre_roll_or_transcription(self):
        stt = RecordingSTT()
        buffer = StreamingSpeechBuffer(stt)
        self.assertEqual(buffer.feed(b"\0\0" * 1600, assistant_originated=True), [])
        self.assertEqual(buffer.pre_roll, b"")
        self.assertEqual(stt.frames, [])
