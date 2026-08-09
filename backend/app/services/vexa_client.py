import asyncio
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Optional

import websockets
from fastapi import HTTPException, status

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import TranscriptSegment

logger = logging.getLogger(__name__)


def extract_google_meet_code(meeting_url: str) -> str:
    """Extracts the clean native Google Meet code (e.g., 'abc-defg-hij') from a URL or raw code."""
    raw = (meeting_url or "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google Meet URL or meeting code is required",
        )

    # If it's a URL, parse path
    if "meet.google.com" in raw or raw.startswith("http"):
        parsed = urllib.parse.urlparse(raw)
        path = parsed.path.strip("/")
        # Path is typically 'abc-defg-hij' or 'lookup/...'
        segments = [s for s in path.split("/") if s]
        if segments:
            raw = segments[-1]

    # Remove query string / fragments if remaining
    raw = re.split(r"[?#]", raw)[0].strip()

    # Validate Google Meet code pattern (typically 3-4-3 letters with hyphens, e.g. xxx-yyyy-zzz)
    code_match = re.search(r"([a-z0-9]{3,4}-[a-z0-9]{3,4}-[a-z0-9]{3,4}|[a-z0-9]{9,12})", raw.lower())
    if code_match:
        return code_match.group(1)

    # Return sanitized fallback if it doesn't contain forbidden URL characters
    cleaned = re.sub(r"[^a-zA-Z0-9\-_]", "", raw)
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract a valid Google Meet meeting code from: '{meeting_url}'",
        )
    return cleaned.lower()


def start_google_meet_bot(
    native_meeting_id: str,
    bot_name: str = "MeetPilot AI",
    transcribe_enabled: bool = True,
) -> dict[str, Any]:
    """Instructs Vexa's API gateway to dispatch a Playwright bot to join the live Google Meet call."""
    api_url = f"{settings.VEXA_API_URL.rstrip('/')}/bots"
    payload = json.dumps({
        "platform": "google_meet",
        "native_meeting_id": native_meeting_id,
        "bot_name": bot_name,
        "transcribe_enabled": transcribe_enabled,
    }).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            "X-API-Key": settings.VEXA_API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            logger.info("Vexa bot successfully dispatched for Google Meet %s: %s", native_meeting_id, data)
            return data
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        logger.error("Vexa POST /bots failed with status %d: %s", err.code, body)
        if err.code == 503 and transcribe_enabled:
            # Fallback: dispatch bot in capture-only mode
            logger.info("Retrying Vexa bot dispatch in capture-only mode for %s...", native_meeting_id)
            return start_google_meet_bot(native_meeting_id, bot_name=bot_name, transcribe_enabled=False)
        elif err.code == 409:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A Vexa bot is already active or registered for meeting {native_meeting_id}",
            )
        elif err.code == 503:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vexa transcription service is not configured or unavailable",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Vexa service error ({err.code}): {body}",
            )
    except Exception as exc:
        logger.exception("Failed connecting to Vexa gateway at %s", api_url)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to reach Vexa gateway: {exc}",
        )


def stop_google_meet_bot(native_meeting_id: str) -> dict[str, Any]:
    """Tells Vexa's bot to gracefully leave the Google Meet room."""
    api_url = f"{settings.VEXA_API_URL.rstrip('/')}/bots/google_meet/{native_meeting_id}"
    req = urllib.request.Request(
        api_url,
        headers={
            "X-API-Key": settings.VEXA_API_KEY,
        },
        method="DELETE",
    )

    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            logger.info("Vexa bot stopped for %s: %s", native_meeting_id, data)
            return data
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        logger.warning("Vexa DELETE /bots returned status %d: %s", err.code, body)
        return {"status": "stopped", "detail": body}
    except Exception as exc:
        logger.warning("Exception calling Vexa DELETE /bots for %s: %s", native_meeting_id, exc)
        return {"status": "stopped", "detail": str(exc)}


def fetch_vexa_audio(meeting_id: Any, native_meeting_id: str) -> Optional[str]:
    """Attempts to retrieve the consolidated master audio recording from Vexa and stores it locally."""
    try:
        from pathlib import Path
        audio_dir = Path(settings.STORAGE_DIR) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        dest_path = audio_dir / f"{meeting_id}.webm"

        base_url = settings.VEXA_API_URL.rstrip("/")
        headers = {"X-API-Key": settings.VEXA_API_KEY}

        # 1. Fetch available recordings from Vexa gateway
        list_req = urllib.request.Request(f"{base_url}/recordings", headers=headers)
        with urllib.request.urlopen(list_req, timeout=10.0) as resp:
            rec_doc = json.loads(resp.read().decode("utf-8"))

        recordings = rec_doc.get("recordings", [])
        if not recordings:
            logger.info("No recordings found in Vexa for meeting %s", native_meeting_id)
            return None

        # Pick the most recent recording
        target_rec = recordings[-1]
        rec_id = target_rec.get("id")
        if not rec_id:
            return None

        # 2. Query master metadata to obtain raw stream URL
        master_req = urllib.request.Request(f"{base_url}/recordings/{rec_id}/master?type=audio", headers=headers)
        with urllib.request.urlopen(master_req, timeout=10.0) as resp:
            master_data = json.loads(resp.read().decode("utf-8"))

        raw_url = master_data.get("raw_url")
        if not raw_url:
            return None

        # 3. Download the assembled master audio bytes
        full_audio_url = f"{base_url}{raw_url}" if raw_url.startswith("/") else raw_url
        audio_req = urllib.request.Request(full_audio_url, headers=headers)
        with urllib.request.urlopen(audio_req, timeout=30.0) as resp:
            audio_bytes = resp.read()
            if audio_bytes and len(audio_bytes) > 500:
                with dest_path.open("wb") as out:
                    out.write(audio_bytes)
                logger.info("Successfully fetched and saved %d audio bytes for live meeting %s", len(audio_bytes), meeting_id)
                return f"local://{dest_path}"

    except Exception as e:
        logger.warning("Vexa audio retrieval failed for meeting %s: %s", native_meeting_id, e)

    return None



def get_vexa_transcript(platform: str, native_meeting_id: str) -> list[dict[str, Any]]:
    """Retrieves the consolidated transcript from Vexa after a meeting finishes."""
    api_url = f"{settings.VEXA_API_URL.rstrip('/')}/transcripts/{platform}/{native_meeting_id}"
    req = urllib.request.Request(
        api_url,
        headers={
            "X-API-Key": settings.VEXA_API_KEY,
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
            segments_raw = doc.get("segments", [])
            normalized = []
            for seg in segments_raw:
                text = (seg.get("text") or "").strip()
                if not text:
                    continue
                start = float(seg.get("start", seg.get("start_time", 0.0)) or 0.0)
                end = float(seg.get("end", seg.get("end_time", start + 1.0)) or (start + 1.0))
                speaker = str(seg.get("speaker") or "Participant").strip()
                normalized.append({
                    "speaker": speaker,
                    "start_time": start,
                    "end_time": max(end, start + 0.1),
                    "text": text,
                })
            return normalized
    except Exception as exc:
        logger.warning("Could not fetch final transcript from Vexa for %s/%s: %s", platform, native_meeting_id, exc)
        return []


async def listen_live_transcript_stream(meeting_id: uuid.UUID, native_meeting_id: str) -> None:
    """Asynchronously connects to Vexa's WebSocket transcript stream and writes chunks into transcript_segments."""
    ws_url = f"{settings.VEXA_WS_URL}?api_key={settings.VEXA_API_KEY}"
    logger.info("Starting live transcript WebSocket consumer for meeting %s (%s)", meeting_id, native_meeting_id)

    max_reconnect_attempts = 10
    attempt = 0

    while attempt < max_reconnect_attempts:
        db = SessionLocal()
        try:
            meeting = db.get(Meeting, meeting_id)
            if not meeting or meeting.status not in (MeetingStatus.in_progress, MeetingStatus.queued):
                logger.info("Meeting %s status is %s; stopping live stream consumer.", meeting_id, meeting.status if meeting else "None")
                break

            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                # 1. Subscribe to meeting channel
                sub_frame = {
                    "action": "subscribe",
                    "meetings": [
                        {"platform": "google_meet", "native_id": native_meeting_id}
                    ]
                }
                await ws.send(json.dumps(sub_frame))
                logger.info("Subscribed to Vexa WS stream for Google Meet %s", native_meeting_id)

                while True:
                    # Check if meeting has ended in DB
                    db.refresh(meeting)
                    if meeting.status not in (MeetingStatus.in_progress, MeetingStatus.queued):
                        logger.info("Meeting %s reached status %s, exiting WS listener.", meeting_id, meeting.status)
                        return

                    try:
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    except asyncio.TimeoutError:
                        continue

                    try:
                        data = json.loads(raw_msg)
                    except Exception:
                        continue

                    # Handle incoming live transcript segment or frame
                    # Vexa frames can have type == 'transcript' or carrying segment data
                    msg_type = data.get("type")
                    if msg_type == "transcript" or ("text" in data and ("speaker" in data or "segment" in data)):
                        seg_data = data.get("segment") or data
                        text = (seg_data.get("text") or "").strip()
                        speaker = str(seg_data.get("speaker") or "Participant").strip()
                        start_time = float(seg_data.get("start", seg_data.get("start_time", 0.0)) or 0.0)
                        end_time = float(seg_data.get("end", seg_data.get("end_time", start_time + 1.0)) or (start_time + 1.0))

                        if text:
                            # Check if segment with same text and close timestamp already exists to prevent duplicate live chunk writes
                            existing = (
                                db.query(TranscriptSegment)
                                .filter(
                                    TranscriptSegment.meeting_id == meeting_id,
                                    TranscriptSegment.text == text,
                                )
                                .first()
                            )
                            if not existing:
                                segment_row = TranscriptSegment(
                                    meeting_id=meeting_id,
                                    speaker=speaker,
                                    start_time=start_time,
                                    end_time=max(end_time, start_time + 0.1),
                                    text=text,
                                    embedding=None,  # Embeddings computed at meeting conclusion
                                )
                                db.add(segment_row)
                                db.commit()
                                logger.debug("Persisted live segment for meeting %s: [%s] %s", meeting_id, speaker, text[:40])

                    elif msg_type == "meeting.status":
                        remote_status = data.get("status")
                        logger.info("Received meeting.status from Vexa for %s: %s", native_meeting_id, remote_status)
                        if remote_status in ("completed", "stopped", "failed"):
                            logger.info("Remote Vexa meeting finished (%s), concluding WS listener.", remote_status)
                            return

        except Exception as exc:
            logger.warning("Error in Vexa live transcript stream (attempt %d/%d): %s", attempt + 1, max_reconnect_attempts, exc)
            attempt += 1
            await asyncio.sleep(2.0)
        finally:
            db.close()
