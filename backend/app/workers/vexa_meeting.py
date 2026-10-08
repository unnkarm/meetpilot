"""Run upstream Vexa; retain MeetPilot's scoped evidence and intelligence pipeline."""
import asyncio
from collections import deque
from datetime import datetime, timezone
import json
import logging
import os
import time
import uuid

import redis
from websockets.legacy.client import connect
from celery.signals import worker_ready
from sqlalchemy import func

from app.core.celery_app import celery_app
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import TranscriptSegment
from app.services.vexa_client import VexaClient, VexaError, VexaUnavailable
from app.services.vexa_recording import sync_recording
from app.workers.meeting_bot import _persist_turn, _publish_insight

logger = logging.getLogger(__name__)
TERMINAL = {"completed", "failed"}


class BridgeSuperseded(Exception):
    """Another worker owns capture; this worker must not stop its bot."""


def maintain_lease(client, lock_key, token):
    # A laptop sleep or slow local inference can let the TTL expire. Recover
    # only an unowned lease; never renew or delete another worker's lease.
    return bool(client.eval(
        "if redis.call('get',KEYS[1]) == ARGV[1] then "
        "return redis.call('expire',KEYS[1],120) "
        "elseif redis.call('exists',KEYS[1]) == 0 then "
        "return redis.call('set',KEYS[1],ARGV[1],'EX',120,'NX') else return 0 end",
        1, lock_key, token))


def finalize_capture(ident, workspace_id, failure=None, *, recover_failed=False):
    """Analyze saved evidence even when capture ended unexpectedly."""
    with SessionLocal() as db:
        meeting = db.get(Meeting, ident)
        allowed = {MeetingStatus.in_progress, MeetingStatus.queued}
        if recover_failed:
            allowed.add(MeetingStatus.failed)
        if meeting is None or meeting.workspace_id != workspace_id or meeting.status not in allowed:
            return False
        end = db.query(func.max(TranscriptSegment.end_time)).filter(TranscriptSegment.meeting_id == ident).scalar()
        meeting.capture_failure_reason = failure
        if failure and end is None and not meeting.audio_url:
            meeting.status = MeetingStatus.failed
            meeting.failure_reason = failure
            db.commit()
            return False
        meeting.duration_seconds = max(meeting.duration_seconds or 0, int(end or 0))
        meeting.status = MeetingStatus.queued
        meeting.failure_reason = None
        meeting.processing_updated_at = datetime.now(timezone.utc)
        db.commit()
    from app.workers.meeting_processor import process_live_meeting
    try:
        process_live_meeting.delay(str(ident))
    except Exception:
        logger.exception("Could not queue saved meeting analysis meeting=%s", ident)
        with SessionLocal() as db:
            meeting = db.get(Meeting, ident)
            if meeting and meeting.workspace_id == workspace_id and meeting.status == MeetingStatus.queued:
                meeting.status = MeetingStatus.failed
                meeting.failure_reason = "Could not queue meeting analysis. Retry processing when the worker is available."
                db.commit()
        return False
    return True


def confirmed_segments(payload: dict) -> list[dict]:
    if payload.get("type") == "transcript":
        return [{"speaker": payload.get("speaker"), **row} for row in payload.get("confirmed", [])
                if isinstance(row, dict) and row.get("completed") is not False]
    if payload.get("type") == "transcription_segment" and payload.get("completed") is True:
        return [payload]
    return []


def voice_event(row: dict, kind: str, speaker=None) -> dict:
    speaker = row.get("speaker") or speaker
    return {"type": kind, "text": str(row.get("text") or "").strip(), "speaker": speaker,
            "language": row.get("language"),
            "utterance_id": str(row.get("segment_id") or f"{speaker}:{row.get('start', row.get('start_time', ''))}")}


def segment_times(row: dict, epoch: float) -> tuple[float, float] | None:
    def relative(value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            # Unix timestamps are absolute, seconds on the recording timeline are relative.
            return max(0, float(value) - epoch if float(value) > 1_000_000_000 else float(value))
        if isinstance(value, str):
            try:
                return relative(float(value))
            except ValueError:
                stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                return max(0, stamp.timestamp() - epoch)
        raise ValueError("Transcript timestamp missing")
    try:
        start = relative(row.get("start", row.get("start_time", row.get("absolute_start_time"))))
        end = relative(row.get("end", row.get("end_time", row.get("absolute_end_time"))))
        return start, max(start + 0.1, end)
    except (ValueError, TypeError, OverflowError):
        return None


def status_event(client, ident, state, text):
    payload = {"kind": "bot_status", "state": state, "text": text, "engine": "vexa"}
    client.setex(f"native-meeting:{ident}:status", 86400, json.dumps(payload))
    _publish_insight(client, ident, payload)


async def run_bridge(ident, workspace_id, meeting_url, bot_name, client, lock_key, token):
    vexa = VexaClient(workspace_id)
    binding_key = f"vexa:meeting:{ident}:binding"
    raw = client.get(binding_key)
    if raw:
        binding = json.loads(raw)
        vexa.binding(ident)
    else:
        status_event(client, ident, "requested", "Starting the upstream Vexa bot")
        with SessionLocal() as db:
            local = db.get(Meeting, ident)
            if local is None or local.workspace_id != workspace_id:
                return
            language = local.transcription_language
        spawned = await asyncio.to_thread(vexa.start, meeting_url, bot_name, language)
        binding = {"workspace_id": str(workspace_id), "provider_id": spawned["id"],
                   "platform": spawned["platform"], "native_id": spawned.get("native_meeting_id") or spawned.get("platform_specific_id"),
                   "epoch": time.time(), "meeting_url": meeting_url}
        client.set(binding_key, json.dumps(binding))
        with SessionLocal() as db:
            meeting = db.get(Meeting, ident)
            if meeting and str(meeting.workspace_id) == str(workspace_id):
                meeting.native_meeting_id = binding["native_id"]
                db.commit()
    recent = deque(maxlen=20)
    seen = set()
    # Re-delivered confirmed rows are harmless after a bridge/Redis restart too.
    with SessionLocal() as db:
        for row in db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == ident):
            seen.add((round(row.start_time, 2), round(row.end_time, 2), row.speaker, row.text))

    async def persist(rows):
        for row in rows:
            text = str(row.get("text") or "").strip()
            times = segment_times(row, binding["epoch"])
            if not text or times is None:
                continue
            speaker = str(row.get("speaker") or "Unknown speaker")
            fingerprint = (round(times[0], 2), round(times[1], 2), speaker, text)
            if fingerprint in seen:
                continue
            # Voice control must not wait for embeddings or passive intelligence.
            client.publish(f"native-meeting:{ident}:transcript", json.dumps(voice_event(row, "final_transcript", speaker)))
            pending = await asyncio.to_thread(_persist_turn, ident, speaker, *times, text,
                                               row.get("language"), recent, client,
                                               row_id=uuid.uuid5(ident, "vexa:" + str(row["segment_id"])) if row.get("segment_id") else None)
            seen.add(fingerprint)
            if pending:
                # Retain the source-backed question alert produced by the shared analysis path.
                _publish_insight(client, ident, pending)

    last_state = None
    stop_sent = False
    ws_url = settings.VEXA_API_URL.rstrip("/").replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    events = asyncio.Queue(maxsize=512)

    async def read_websocket():
        while True:
            try:
                async with connect(ws_url, extra_headers={"X-API-Key": await asyncio.to_thread(vexa.api_key)},
                                   open_timeout=10, max_size=4_000_000) as socket:
                    await socket.send(json.dumps({"action": "subscribe", "meetings": [{"platform": binding["platform"], "native_id": binding["native_id"]}]}))
                    async for message in socket:
                        payload = json.loads(message)
                        incoming_id = (payload.get("meeting") or {}).get("id")
                        if incoming_id is not None and int(incoming_id) != binding["provider_id"]:
                            continue
                        # Forward recognition immediately, even while persistence is busy.
                        for row in confirmed_segments(payload):
                            client.publish(f"native-meeting:{ident}:transcript", json.dumps(voice_event(row, "final_transcript")))
                        if payload.get("type") == "transcript":
                            for row in payload.get("pending", []):
                                if isinstance(row, dict) and str(row.get("text") or "").strip():
                                    client.publish(f"native-meeting:{ident}:transcript", json.dumps(
                                        voice_event(row, "partial_transcript", payload.get("speaker"))))
                        await events.put(payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Vexa websocket disconnected meeting=%s; recovering through scoped REST", ident)
                await asyncio.sleep(2)

    async def renew_lease():
        while True:
            await asyncio.sleep(20)
            if not maintain_lease(client, lock_key, token):
                return

    background = [asyncio.create_task(read_websocket()), asyncio.create_task(renew_lease())]
    try:
        deadline = time.monotonic() + 7200
        while time.monotonic() < deadline:
            if not maintain_lease(client, lock_key, token):
                raise BridgeSuperseded()
            with SessionLocal() as db:
                local = db.get(Meeting, ident)
                if local is None or str(local.workspace_id) != str(workspace_id):
                    await asyncio.to_thread(vexa.stop, binding["platform"], binding["native_id"])
                    return
                wants_stop = local.status != MeetingStatus.in_progress
            if wants_stop and not stop_sent:
                try:
                    await asyncio.to_thread(vexa.stop, binding["platform"], binding["native_id"])
                except VexaUnavailable:
                    await asyncio.sleep(5)
                    continue
                stop_sent = True
            try:
                current = await asyncio.to_thread(vexa.meeting, binding["provider_id"])
                transcript = await asyncio.to_thread(vexa.transcript, binding["provider_id"])
            except VexaUnavailable:
                status_event(client, ident, "reconnecting", "Vexa is reconnecting; captured turns will be recovered")
                await asyncio.sleep(5)
                continue
            state = current.get("status", "joining")
            if current.get("start_time") and not binding.get("timeline_anchored"):
                binding["epoch"] = datetime.fromisoformat(current["start_time"].replace("Z", "+00:00")).timestamp()
                binding["timeline_anchored"] = True
                client.set(binding_key, json.dumps(binding))
            if state != last_state:
                captions = {"requested": "Vexa bot is queued", "joining": "Vexa is opening the meeting",
                            "awaiting_admission": "Vexa is waiting for the host to admit MeetPilot AI Bot",
                            "active": "Vexa bot joined; listening and transcribing locally",
                            "needs_human_help": "The meeting requires attention in the local Vexa browser",
                            "stopping": "Vexa is leaving and saving the transcript",
                            "completed": "Vexa finished the meeting", "failed": "Vexa could not join or continue the meeting"}
                status_event(client, ident, state, captions.get(state, f"Vexa bot: {state}"))
                last_state = state
            # Exact provider row lookup prevents old meetings on the same link from leaking in.
            await persist([row for row in transcript.get("segments", []) if row.get("completed") is True])
            if state in TERMINAL:
                # Last recording chunk and collector writes can trail the lifecycle callback.
                await asyncio.sleep(2)
                transcript = await asyncio.to_thread(vexa.transcript, binding["provider_id"])
                await persist([row for row in transcript.get("segments", []) if row.get("completed") is True])
                try:
                    await asyncio.to_thread(sync_recording, ident, workspace_id, vexa)
                except Exception:
                    logger.exception("Vexa recording download failed meeting=%s", ident)
                if state == "failed":
                    reason = (current.get("data") or {}).get("reason")
                    fallback = ("The meeting bot disconnected unexpectedly" if current.get("start_time")
                                else "The meeting bot could not join")
                    raise VexaError(reason or fallback)
                return
            until = time.monotonic() + 5
            while time.monotonic() < until:
                try:
                    payload = await asyncio.wait_for(events.get(), max(0.1, until - time.monotonic()))
                except asyncio.TimeoutError:
                    break
                if payload.get("type") in {"error", "bridge_error"}:
                    raise VexaError("Vexa refused the workspace transcript subscription")
                incoming_id = (payload.get("meeting") or {}).get("id")
                if incoming_id is not None and int(incoming_id) != binding["provider_id"]:
                    continue
                await persist(confirmed_segments(payload))
        await asyncio.to_thread(vexa.stop, binding["platform"], binding["native_id"])
    finally:
        for task in background:
            task.cancel()
        await asyncio.gather(*background, return_exceptions=True)


@celery_app.task(name="run_vexa_meeting_bot")
def run_vexa_meeting_bot_task(meeting_id: str, meeting_url: str, bot_name: str = "MeetPilot AI Bot"):
    ident = uuid.UUID(meeting_id)
    client = redis.Redis.from_url(settings.REDIS_URL)
    lock_key = f"native-meeting:{ident}:lock"
    token = uuid.uuid4().hex
    if not client.set(lock_key, token, nx=True, ex=120):
        return
    try:
        with SessionLocal() as db:
            meeting = db.get(Meeting, ident)
            if meeting is None or meeting.status != MeetingStatus.in_progress:
                return
            workspace_id = meeting.workspace_id
        asyncio.run(run_bridge(ident, workspace_id, meeting_url, bot_name, client, lock_key, token))
        finalize_capture(ident, workspace_id)
    except BridgeSuperseded:
        logger.info("Vexa bridge handed over to another worker meeting=%s", ident)
    except Exception as exc:
        logger.exception("Vexa bridge failed meeting=%s", ident)
        if not maintain_lease(client, lock_key, token):
            logger.info("Ignoring error from superseded Vexa bridge meeting=%s", ident)
            return
        message = str(exc) if isinstance(exc, VexaError) else "Vexa integration failed; check local service logs"
        completed = False
        if "workspace_id" in locals():
            try:
                vexa = VexaClient(workspace_id)
                binding = vexa.binding(ident)
                # A terminal callback can race a transport failure. Confirm the
                # provider's lifecycle before turning a natural end into an error.
                upstream = vexa.meeting(binding["provider_id"])
                completed = upstream.get("status") == "completed"
                if upstream.get("status") not in TERMINAL and client.get(lock_key) == token.encode():
                    vexa.stop(binding["platform"], binding["native_id"])
                sync_recording(ident, workspace_id, vexa)
            except Exception:
                logger.warning("Could not reconcile Vexa capture meeting=%s", ident, exc_info=True)
            status_event(client, ident, "completed" if completed else "failed",
                         "Meeting ended; preparing analysis" if completed else message)
            finalize_capture(ident, workspace_id, None if completed else message)
    finally:
        client.eval("if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end",
                    1, lock_key, token)
        client.close()


def resume_existing_bridges() -> int:
    queued = 0
    client = redis.Redis.from_url(settings.REDIS_URL)
    try:
        with SessionLocal() as db:
            meetings = db.query(Meeting).filter(Meeting.source == "live", Meeting.status.in_(
                [MeetingStatus.in_progress, MeetingStatus.failed])).all()
            for meeting in meetings:
                if not client.exists(f"vexa:meeting:{meeting.id}:binding"):
                    continue
                vexa = VexaClient(meeting.workspace_id)
                try:
                    binding = vexa.binding(meeting.id)
                    upstream = vexa.meeting(binding["provider_id"])
                    if upstream.get("status") in TERMINAL and meeting.status == MeetingStatus.failed:
                        continue
                    url = binding.get("meeting_url") or upstream.get("constructed_meeting_url")
                    if not url:
                        continue
                    # Recover only a failed BRIDGE whose independent bot still runs.
                    if meeting.status == MeetingStatus.failed:
                        if upstream.get("status") != "active":
                            continue
                        meeting.status = MeetingStatus.in_progress
                        meeting.failure_reason = None
                        db.commit()
                    ttl = client.ttl(f"native-meeting:{meeting.id}:lock")
                    run_vexa_meeting_bot_task.apply_async(args=[str(meeting.id), url, "MeetPilot AI Bot"],
                                                         queue="meeting_bot", countdown=max(0, ttl) + 1)
                    queued += 1
                except Exception:
                    logger.exception("Could not resume Vexa bridge meeting=%s", meeting.id)
    finally:
        client.close()
    return queued


@worker_ready.connect
def resume_after_worker_restart(**kwargs):
    if os.getenv("MEETPILOT_VEXA_BRIDGE_WORKER") == "true":
        logger.info("Resumed %s Vexa meeting bridges", resume_existing_bridges())
