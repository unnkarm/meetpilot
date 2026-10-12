import io
import shutil
import tempfile
import unittest
import uuid
import wave
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.core.app_config import APP_CONFIG
from app.api.routes.meetings import DecisionUpdateRequest, _can_retry, update_decision
from app.api.routes.tasks import _resolve_assignee
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import TranscriptSegment
from app.services.storage import LocalStorageProvider
from app.services.audio_chunker import cleanup_temp_chunks, split_audio
from app.workers.meeting_processor import _source_segment, _supported_by_source


class ProcessingAndEditTests(unittest.TestCase):
    def test_evidence_timestamp_must_match_persisted_segment(self):
        segment = TranscriptSegment(id=uuid.uuid4(), meeting_id=uuid.uuid4(),
                                    start_time=42.0, end_time=53.0, speaker="Alice", text="We agreed.")
        self.assertIs(_source_segment("00:45", [segment]), segment)
        self.assertIsNone(_source_segment("02:00", [segment]))
        self.assertIsNone(_source_segment("invented", [segment]))

    def test_hallucinated_task_is_not_supported_by_its_cited_speech(self):
        source = TranscriptSegment(id=uuid.uuid4(), meeting_id=uuid.uuid4(),
                                   start_time=38.0, end_time=44.0, speaker="Noah",
                                   text="Yes, I will do it.")
        self.assertFalse(_supported_by_source("Test Upload First Feature", source))
        source.text = "Noah, please prepare the upload screen."
        self.assertTrue(_supported_by_source("Prepare Upload Screen", source))

    def test_only_failed_or_stale_meeting_can_retry(self):
        meeting = Meeting(id=uuid.uuid4(), workspace_id=uuid.uuid4(), created_by=uuid.uuid4(),
                          title="Review", status=MeetingStatus.completed)
        self.assertFalse(_can_retry(meeting))
        meeting.status = MeetingStatus.analyzing
        meeting.processing_updated_at = datetime.now(timezone.utc)
        self.assertFalse(_can_retry(meeting))
        meeting.processing_updated_at -= timedelta(hours=3)
        self.assertTrue(_can_retry(meeting))
        meeting.status = MeetingStatus.failed
        self.assertTrue(_can_retry(meeting))

    def test_decision_edit_preserves_source_evidence(self):
        meeting_id = uuid.uuid4()
        decision = Decision(id=uuid.uuid4(), meeting_id=meeting_id, topic="Old", outcome="Old outcome",
                            source_segment_id=uuid.uuid4(), transcript_timestamp="01:02")
        db = MagicMock()
        db.query().filter().first.return_value = decision
        with patch("app.api.routes.meetings.get_meeting_for_member"), patch("app.api.routes.meetings.require_manager"):
            updated = update_decision(meeting_id, decision.id,
                                      DecisionUpdateRequest(outcome="Corrected outcome"),
                                      SimpleNamespace(id=uuid.uuid4()), db)
        self.assertEqual(updated.outcome, "Corrected outcome")
        self.assertIsNotNone(updated.source_segment_id)
        self.assertEqual(updated.transcript_timestamp, "01:02")

    def test_nonmember_assignee_is_rejected(self):
        db = MagicMock()
        db.query().join().filter().first.return_value = None
        with self.assertRaises(HTTPException) as raised:
            _resolve_assignee(db, uuid.uuid4(), "Outsider")
        self.assertEqual(raised.exception.status_code, 422)

    def test_local_storage_rejects_traversal_and_oversize_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = replace(APP_CONFIG, storage_dir=directory,
                              uploads=replace(APP_CONFIG.uploads, max_audio_bytes=4))
            with patch("app.services.storage.APP_CONFIG", changed):
                storage = LocalStorageProvider()
                with self.assertRaises(ValueError):
                    storage.get("local://../../outside.txt")
                upload = SimpleNamespace(filename="meeting.wav", file=io.BytesIO(b"12345"))
                with self.assertRaisesRegex(ValueError, "size limit"):
                    storage.save(upload, uuid.uuid4())
                self.assertEqual(list((Path(directory) / "audio").iterdir()), [])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_audio_chunking_has_bounded_overlap_and_removes_temp_files(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "eleven_seconds.wav"
            with wave.open(str(audio), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(8000)
                output.writeframes(b"\x00\x00" * 8000 * 11)
            chunks = split_audio(audio, "chunk-test", chunk_length_ms=5000, overlap_ms=1000)
            self.assertEqual([chunk["start_offset_ms"] for chunk in chunks], [0, 4000, 8000])
            self.assertTrue(all(chunk["path"].stat().st_size > 0 for chunk in chunks))
            chunk_dir = chunks[0]["path"].parent
            cleanup_temp_chunks(chunks)
            self.assertFalse(chunk_dir.exists())
