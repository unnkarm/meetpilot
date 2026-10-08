"""Copy the owned Vexa recording to MeetPilot's authenticated local audio store."""
from pathlib import Path
import subprocess
import uuid
import wave

import httpx

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.meeting import Meeting
from app.services.storage import get_storage_provider


def sync_recording(meeting_id: uuid.UUID, workspace_id: uuid.UUID, vexa) -> str | None:
    binding = vexa.binding(meeting_id)
    recordings = vexa.request("GET", f"/recordings?meeting_id={binding['provider_id']}").get("recordings", [])
    recording = next((row for row in recordings if row.get("meeting_id") == binding["provider_id"]), None)
    if recording is None:
        return None
    metadata = vexa.request("GET", f"/recordings/{int(recording['id'])}/master?type=audio")
    raw_url = metadata.get("raw_url")
    if not raw_url or not raw_url.startswith(f"/recordings/{int(recording['id'])}/media/"):
        raise ValueError("Vexa did not return an owned recording download")
    suffix = Path(metadata.get("storage_path") or "audio.webm").suffix.lower()
    if suffix not in {".wav", ".webm", ".ogg", ".mp3", ".m4a"}:
        raise ValueError("Unsupported Vexa recording format")
    folder = Path(settings.STORAGE_DIR).resolve() / str(workspace_id) / str(meeting_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("vexa-recording" + suffix)
    temporary = target.with_suffix(suffix + ".part")
    try:
        with httpx.stream("GET", settings.VEXA_API_URL.rstrip("/") + raw_url,
                          headers={"X-API-Key": vexa.api_key()}, timeout=120) as response:
            response.raise_for_status()
            total = 0
            with temporary.open("wb") as stream:
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > 600_000_000:
                        raise ValueError("Recording exceeds the local 600MB limit")
                    stream.write(chunk)
            if total == 0:
                raise ValueError("Vexa recording is empty")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    # MediaRecorder WebM often has no finite duration/seek index. A finalized
    # PCM WAV gives both browser playback and Whisper an exact frame count.
    normalized = target.with_name("vexa-playback.wav")
    wav_temporary = normalized.with_suffix(".wav.part")
    try:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(target),
                        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                        "-f", "wav", str(wav_temporary)], check=True, timeout=180,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with wave.open(str(wav_temporary), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
        wav_temporary.replace(normalized)
    finally:
        wav_temporary.unlink(missing_ok=True)
    with SessionLocal() as db:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None or meeting.workspace_id != workspace_id:
            raise ValueError("Recording's MeetPilot workspace changed")
        meeting.audio_url = get_storage_provider().get_url(normalized)
        meeting.duration_seconds = int(duration)
        db.commit()
        return meeting.audio_url
