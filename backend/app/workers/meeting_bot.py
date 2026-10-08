"""Dedicated local Chromium bot: remote PCM -> local STT -> evidence-linked turns."""

import asyncio
import audioop
import base64
import json
import logging
import os
import re
import time
import uuid
from array import array
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path

import redis
from playwright.async_api import async_playwright

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.app_config import APP_CONFIG
from app.database.session import SessionLocal
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus
from app.models.transcript import TranscriptSegment
from app.services.native_meeting import CAPTURE_SCRIPT, MeetingTarget, native_insights, parse_meeting_target
from app.services.knowledge_retriever import KnowledgeRetriever
from app.services.pilot_phase1 import _verified_participant, classify_live_statement, safely_process_live_segment
from app.services.pilot_streaming_stt import StreamingSpeechBuffer, get_stt_provider
from app.workers import native_input
from app.services.bot_browser import browser_options, has_google_session, import_auth_state, locked_profile, profile_path, save_auth_state
from app.services.bot_admission import JoinState, JOIN_PATTERN, WAITING_COPY, ERROR_MESSAGES, classify_page
from app.services.bot_console import browser_console

logger = logging.getLogger(__name__)


class MeetingJoinError(RuntimeError):
    """Typed terminal admission failure, suitable for user-facing diagnostics."""

    def __init__(self, message: str, code: str = "join_failed"):
        super().__init__(message)
        self.code = code


@dataclass
class TrackState:
    speaker: str
    buffer: StreamingSpeechBuffer
    started_at: float | None = None
    hints: Counter = field(default_factory=Counter)
    last_hint_at: float = 0.0
    ambiguous_hints: int = 0


async def _visible_button(page, pattern: str, timeout_ms: int = 25000):
    button = page.get_by_role("button", name=re.compile(pattern, re.IGNORECASE)).first
    await button.wait_for(state="visible", timeout=timeout_ms)
    return button


async def _join_page_text(page) -> str:
    parts = []
    for frame in page.frames:
        try:
            parts.append((await frame.locator("body").inner_text(timeout=1000))[:1200])
        except Exception:
            continue
    return " ".join(parts).replace("’", "'").casefold()


async def _join_rejection(page) -> str | None:
    state = classify_page(await _join_page_text(page), page.url)
    return ERROR_MESSAGES.get(state)


async def _click_join_control(page, pattern: str, *, native: bool = False) -> bool:
    for frame in page.frames:
        button = frame.get_by_role("button", name=re.compile(pattern, re.IGNORECASE)).first
        try:
            if await button.count() and await button.is_visible() and await button.is_enabled():
                if native:
                    try:
                        await native_input.click(page, button)
                    except Exception as exc:
                        logger.warning("Native click unavailable (%s); using named Playwright control", type(exc).__name__)
                        await button.click(timeout=3000)
                else:
                    await button.click(timeout=3000)
                return True
        except Exception:
            continue
    return False


async def _click_google_join_fallback(page) -> bool:
    # Never click arbitrary jsname/span buttons: "Return to home screen" has
    # the same structure as the CTA. The named, anchored selector is sufficient.
    return await _click_join_control(page, JOIN_PATTERN, native=True)


async def _has_visible_control(page, pattern: str) -> bool:
    for frame in page.frames:
        button = frame.get_by_role("button", name=re.compile(pattern, re.IGNORECASE)).first
        try:
            if await button.count() and await button.is_visible():
                return True
        except Exception:
            continue
    return False


async def _is_admitted(page, platform: str) -> bool:
    if platform != "google_meet":
        return await _has_visible_control(page, r"Leave call|Leave meeting|Hang up|End call|^Leave$")
    text = await _join_page_text(page)
    if any(phrase in text for phrase in WAITING_COPY + (
        "what's your name?", "ask to join", "by joining, you agree to the terms of service",
    )):
        return False
    try:
        # Google Meet also creates media streams for the prejoin self-preview;
        # only in-call DOM evidence can confirm that the host admitted us.
        labels = await page.locator("[data-participant-id]").evaluate_all(
            "els => els.map(el => el.getAttribute('aria-label') || el.textContent || '')"
        )
        if any(label.strip() and not re.search(r"visual_effects|backgrounds and effects", label, re.I)
               for label in labels):
            return True
        if await page.locator("[data-self-name]").count():
            return True
        for selector in ('button[aria-label*="Present now"]', 'button[aria-label*="Share screen"]'):
            control = page.locator(selector).first
            if await control.count() and await control.is_visible():
                return True
    except Exception:
        pass
    return False


async def _visible_name_field(page, platform: str):
    # Never type a bot name into an arbitrary search/passcode field.
    selectors = ['input[placeholder*="name" i]', 'input[aria-label*="name" i]',
                 'input[data-testid="prejoin-display-name-input"]', 'input#input-for-name']
    if platform == "google_meet":
        selectors.append('input[jsname][type="text"]:not([aria-hidden="true"])')
    for frame in page.frames:
        for selector in selectors:
            locator = frame.locator(selector).first
            if await locator.count() and await locator.is_visible():
                return locator
    return None


async def _has_challenge(page) -> bool:
    for frame in await page.locator('iframe[src*="recaptcha"]').all():
        if await frame.is_visible():
            box = await frame.bounding_box()
            if box and box["width"] >= 120 and box["height"] >= 40:
                return True
    return False


async def _join(page, target: MeetingTarget, bot_name: str, *, on_state=None,
                should_stop=None, authenticated: bool = False,
                prejoin_timeout: float = 120, admission_timeout: float = 300,
                poll_interval: float = 0.7) -> None:
    await page.goto(target.url, wait_until="domcontentloaded", timeout=60000)
    await page.bring_to_front()
    submitted_at = None
    prejoin_deadline = time.monotonic() + prejoin_timeout
    challenge_since = None
    last_state = None
    while True:
        if should_stop and await should_stop():
            raise MeetingJoinError("The meeting was stopped while the bot was joining.", "cancelled")
        text = await _join_page_text(page)
        name_field = await _visible_name_field(page, target.platform)
        state = classify_page(text, page.url,
                              in_call=await _is_admitted(page, target.platform),
                              join_visible=await _has_visible_control(page, JOIN_PATTERN),
                              name_visible=name_field is not None,
                              challenge_visible=await _has_challenge(page))
        if state != last_state:
            logger.info("Native bot admission platform=%s state=%s", target.platform, state.value)
            if on_state:
                await on_state(state)
            last_state = state
        if state == JoinState.ADMITTED:
            return
        if state in ERROR_MESSAGES:
            raise MeetingJoinError(ERROR_MESSAGES[state], state.value)
        now = time.monotonic()
        if state == JoinState.CHALLENGE:
            challenge_since = challenge_since or now
            if now - challenge_since >= 120:
                raise MeetingJoinError("Browser verification was not completed. Open the local bot browser to complete verification before retrying.", state.value)
            await asyncio.sleep(poll_interval)
            continue
        challenge_since = None
        if state == JoinState.WAITING:
            submitted_at = submitted_at or now
        if submitted_at is not None:
            # Submission is a one-way transition. Do not fill, click, or navigate
            # while waiting for the provider's DOM to catch up or the host to admit.
            if now - submitted_at >= admission_timeout:
                raise MeetingJoinError(f"The bot requested entry but the host did not admit it within {int(admission_timeout)} seconds. Ask the host to admit {bot_name}.", "admission_timeout")
            await asyncio.sleep(poll_interval)
            continue
        if now >= prejoin_deadline:
            raise MeetingJoinError("No supported join control appeared. Check the workspace-scoped screenshot and meeting account requirements.", "prejoin_timeout")
        if target.platform == "teams" and await _click_join_control(page, r"^(Continue on this browser|Join on the web|Continue without signing in)$"):
            await asyncio.sleep(poll_interval)
            continue
        if target.platform == "zoom" and await _click_join_control(page, r"^Join from your browser$"):
            await asyncio.sleep(poll_interval)
            continue
        if name_field is not None:
            if authenticated and target.platform == "google_meet":
                raise MeetingJoinError("The saved Google bot session is signed out. Sign in again using workspace bot setup.", "auth_session_expired")
            if await name_field.input_value() != bot_name:
                await native_input.fill(page, name_field, bot_name)
        # These labels describe the current active devices. Do not toggle a
        # device already off. The virtual mic is unmuted only for actual TTS.
        await _click_join_control(page, r"^(Turn off camera|Turn off video|Disable camera)(?:\s*\([^)]+\))?$", native=target.platform == "google_meet")
        await _click_join_control(page, r"^(Turn off microphone|Mute microphone|Mute)(?:\s*\([^)]+\))?$", native=target.platform == "google_meet")
        if await _click_join_control(page, r"^(Continue without an account|Use without an account)$"):
            await asyncio.sleep(poll_interval)
            continue
        if await _click_join_control(page, JOIN_PATTERN, native=target.platform == "google_meet"):
            submitted_at = time.monotonic()
        await asyncio.sleep(poll_interval)


async def _speaker_hint(page) -> str | None:
    try:
        return await page.evaluate("""() => {
          const els = document.querySelectorAll('[data-is-speaking="true"], [aria-label*="speaking" i], [aria-label*="talking" i]');
          const names = new Set();
          for (const el of els) {
            const raw = el.getAttribute('data-participant-name') || el.getAttribute('aria-label') || '';
            const name = raw.replace(/\\b(is speaking|speaking|is talking|talking)\\b/ig, '').replace(/[,:-]+$/g, '').trim();
            if (name && name.length <= 80) names.add(name);
          }
          return names.size === 1 ? [...names][0] : null;
        }""")
    except Exception:
        return None


def _publish_insight(client: redis.Redis, meeting_id: uuid.UUID, payload: dict) -> None:
    encoded = json.dumps(payload)
    key = f"native-meeting:{meeting_id}:insights-recent"
    client.lpush(key, encoded)
    client.ltrim(key, 0, 19)
    client.expire(key, 86400)
    client.publish(f"native-meeting:{meeting_id}:insights", encoded)


def _persist_turn(meeting_id: uuid.UUID, speaker: str, start: float, end: float,
                  text: str, language: str | None, recent: deque[str], client: redis.Redis,
                  *, row_id: uuid.UUID | None = None) -> dict | None:
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None or meeting.status not in {MeetingStatus.in_progress, MeetingStatus.queued}:
            return None
        if row_id is not None and db.get(TranscriptSegment, row_id) is not None:
            return None
        row = TranscriptSegment(meeting_id=meeting_id, speaker=speaker, start_time=max(0, start),
                                end_time=max(start + 0.1, end), text=text, language_code=language)
        if row_id is not None:
            row.id = row_id
        db.add(row)
        db.commit()
        if speaker and not db.query(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.name == speaker,
        ).first():
            db.add(MeetingParticipant(meeting_id=meeting_id, name=speaker, role="Participant"))
            db.commit()
        safely_process_live_segment(db, meeting, row)
        candidate = classify_live_statement(text)
        owner_verified = bool(candidate and candidate.assignee_name and
                              _verified_participant(db, meeting, candidate.assignee_name))
        for insight in native_insights(text, list(recent), owner_verified=owner_verified):
            payload = {**insight, "meeting_id": str(meeting_id), "source_segment_id": str(row.id),
                       "speaker": speaker, "timestamp": round(row.start_time, 2), "source_quote": text[:300]}
            _publish_insight(client, meeting_id, payload)
        recent.append(text)
        if text.strip().endswith("?"):
            try:
                matches = KnowledgeRetriever(db, meeting.workspace_id).retrieve(text)
                related = next((item for item in matches if item.id != f"transcript:{row.id}"), None)
                if related:
                    _publish_insight(client, meeting_id, {
                        "kind": "rag_context", "text": related.text[:220],
                        "meeting_id": str(meeting_id), "source_segment_id": str(row.id),
                        "speaker": speaker, "timestamp": round(row.start_time, 2),
                        "source_quote": text[:300], "related_source": related.citation,
                    })
            except Exception:
                logger.exception("Local RAG retrieval failed meeting=%s", meeting_id)
            return {"kind": "unanswered_question", "text": "Question has not received a spoken response",
                    "confidence": 0.65, "meeting_id": str(meeting_id), "source_segment_id": str(row.id),
                    "speaker": speaker, "timestamp": round(row.start_time, 2), "source_quote": text[:300]}
        return None
    finally:
        db.close()


async def _speak_loop(page, meeting_id: uuid.UUID, client: redis.Redis, stopping: asyncio.Event,
                      playback_state: dict | None = None):
    playback_state = playback_state if playback_state is not None else {}
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(f"native-meeting:{meeting_id}:tts")
    playback: asyncio.Task | None = None

    async def play(payload: dict) -> None:
        ident = payload.get("interaction_id")
        playback_state.update(speaking=True, interaction_id=ident)
        try:
            # The bot joins muted; only its synthesized voice may open the mic.
            await _click_join_control(page, r"^(Turn on microphone|Unmute microphone|Unmute)(?:\s*\([^)]+\))?$")
            await page.evaluate("wav => window.__meetpilotPlayWav(wav)", payload["wav_base64"])
            event = "playback_complete"
        except asyncio.CancelledError:
            event = "playback_interrupted"
        except Exception:
            logger.exception("Native bot WAV playback failed meeting=%s", meeting_id)
            event = "playback_interrupted"
        finally:
            if playback_state.get("interaction_id") == ident:
                playback_state["speaking"] = False
                await _click_join_control(page, r"^(Turn off microphone|Mute microphone|Mute)(?:\s*\([^)]+\))?$")
        client.publish(f"native-meeting:{meeting_id}:tts-events",
                       json.dumps({"type": event, "interaction_id": payload.get("interaction_id")}))

    try:
        while not stopping.is_set():
            message = await asyncio.to_thread(pubsub.get_message, timeout=1)
            if not message:
                continue
            try:
                payload = json.loads(message["data"])
                if payload.get("type") == "stop":
                    await page.evaluate("window.__meetpilotStopWav()")
                    if playback and not playback.done():
                        playback.cancel()
                        await asyncio.gather(playback, return_exceptions=True)
                    continue
                if payload.get("type") == "play":
                    if playback and not playback.done():
                        await page.evaluate("window.__meetpilotStopWav()")
                        playback.cancel()
                        await asyncio.gather(playback, return_exceptions=True)
                    playback = asyncio.create_task(play(payload))
            except Exception:
                logger.exception("Native bot WAV playback failed meeting=%s", meeting_id)
    finally:
        if playback and not playback.done():
            await page.evaluate("window.__meetpilotStopWav()")
            playback.cancel()
            await asyncio.gather(playback, return_exceptions=True)
        pubsub.close()


async def run_native_meeting_bot(meeting_id: uuid.UUID, target: MeetingTarget, bot_name: str,
                                 client: redis.Redis, lock_token: str) -> None:
    with SessionLocal() as db:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None:
            raise MeetingJoinError("Meeting record no longer exists")
        workspace_id = meeting.workspace_id
    frames: asyncio.Queue[tuple[str, bytes, float, str | None]] = asyncio.Queue(maxsize=1200)
    tracks: dict[str, TrackState] = {}
    transcriber = get_stt_provider()
    recent: deque[str] = deque(maxlen=20)
    pending_questions: deque[tuple[float, dict]] = deque()
    stopping = asyncio.Event()
    started = time.time()
    dropped = 0
    playback_state = {"speaking": False}
    capturing = False
    async with async_playwright() as playwright:
        folder = profile_path(workspace_id, target.platform)
        profile_lock = locked_profile(folder)
        profile_lock.__enter__()
        try:
            context = await playwright.chromium.launch_persistent_context(str(folder), **browser_options())
            await import_auth_state(context, folder, workspace_id)
        except BaseException:
            profile_lock.__exit__(None, None, None)
            raise
        async def on_frame(_source, track_id, samples, timestamp_ms, hint=None):
            nonlocal dropped
            if not isinstance(track_id, str) or not isinstance(samples, list) or len(samples) > 8192:
                return
            pcm = array("h", samples).tobytes()
            if not capturing:
                return
            # Detect human energy at ingestion, before queued Whisper work.
            if playback_state.get("speaking") and audioop.rms(pcm, 2) >= APP_CONFIG.pilot.vad_rms_threshold:
                playback_state["speaking"] = False
                client.publish(f"native-meeting:{meeting_id}:tts", json.dumps({"type": "stop"}))
                client.publish(f"native-meeting:{meeting_id}:tts-events", json.dumps({"type": "pilot_interrupted"}))
            # Authorized Pilot sockets may opt into the bot's remote audio.
            client.publish(f"native-meeting:{meeting_id}:pcm", json.dumps({"track_id": track_id, "pcm_base64": base64.b64encode(pcm).decode("ascii")}))
            if frames.full():
                # Fail visibly instead of silently producing a transcript with
                # missing speech when local inference cannot keep up.
                dropped += 1
                return
            hint = hint if isinstance(hint, str) and 0 < len(hint) <= 80 else None
            frames.put_nowait((track_id[:120], pcm, timestamp_ms / 1000, hint))

        await context.expose_binding("__meetpilotFrame", on_frame)
        await context.add_init_script(CAPTURE_SCRIPT)
        page = await context.new_page()
        console = None
        try:
            try:
                async def report_state(state):
                    nonlocal console
                    if state == JoinState.CHALLENGE and console is None:
                        console = browser_console()
                        console.__enter__()
                    labels = {
                        JoinState.PREJOIN: "Preparing the meeting browser",
                        JoinState.WAITING: f"Waiting for the host to admit {bot_name}",
                        JoinState.ADMITTED: "Bot admitted; capturing meeting audio",
                        JoinState.CHALLENGE: "Complete browser verification at http://localhost:6080/vnc.html?autoconnect=true",
                    }
                    payload = {"kind": "bot_status", "state": state.value,
                               "text": labels.get(state, ERROR_MESSAGES.get(state, "Loading meeting page")),
                               "source_segment_id": "bot-status", "timestamp": 0, "speaker": "", "source_quote": ""}
                    client.setex(f"native-meeting:{meeting_id}:status", 86400, json.dumps(payload))
                    _publish_insight(client, meeting_id, payload)

                async def should_stop():
                    with SessionLocal() as db:
                        record = db.get(Meeting, meeting_id)
                        return record is None or record.status != MeetingStatus.in_progress

                await _join(page, target, bot_name, on_state=report_state,
                            should_stop=should_stop, authenticated=await has_google_session(context))
                # Discard prejoin audio: it is not meeting evidence.
                while not frames.empty():
                    frames.get_nowait()
                started = time.time()
                capturing = True
            except Exception:
                # Keep diagnostics local and scoped to the meeting workspace.
                try:
                    with SessionLocal() as db:
                        meeting = db.get(Meeting, meeting_id)
                        workspace_id = meeting.workspace_id if meeting else None
                    if workspace_id:
                        folder = Path(settings.STORAGE_DIR) / "bot_diagnostics" / str(workspace_id)
                        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
                        screenshot = folder / f"{meeting_id}.png"
                        await page.screenshot(path=str(screenshot), full_page=True)
                        os.chmod(screenshot, 0o600)
                        logger.error("Native bot join screenshot workspace=%s meeting=%s path=%s",
                                     workspace_id, meeting_id, screenshot)
                except Exception:
                    logger.exception("Could not save local bot join screenshot meeting=%s", meeting_id)
                raise
            logger.info("Native bot joined meeting=%s platform=%s", meeting_id, target.platform)
            speaker_task = asyncio.create_task(_speak_loop(page, meeting_id, client, stopping, playback_state))
            try:
                last_status_check = 0.0
                while True:
                    if dropped:
                        raise RuntimeError("Local STT cannot keep up with meeting audio. The input buffer filled; use a smaller Whisper model or fewer concurrent speakers.")
                    now = time.time()
                    if now - last_status_check >= 2:
                        last_status_check = now
                        capture_errors = await page.evaluate("window.__meetpilotCaptureErrors || []")
                        if capture_errors:
                            raise RuntimeError(f"Meeting audio capture failed: {capture_errors[0]}")
                        lock_key = f"native-meeting:{meeting_id}:lock"
                        if client.get(lock_key) != lock_token.encode():
                            raise RuntimeError("Native bot lock was lost")
                        client.expire(lock_key, 7200)
                        with SessionLocal() as db:
                            meeting = db.get(Meeting, meeting_id)
                            if meeting is None or meeting.status != MeetingStatus.in_progress:
                                capturing = False
                                if frames.empty():
                                    break
                    while pending_questions and now - pending_questions[0][0] >= 20:
                        _, alert = pending_questions.popleft()
                        _publish_insight(client, meeting_id, alert)
                    try:
                        track_id, pcm, timestamp, hint = await asyncio.wait_for(frames.get(), timeout=1)
                    except asyncio.TimeoutError:
                        continue
                    if track_id not in tracks:
                        tracks[track_id] = TrackState(f"Speaker {len(tracks) + 1}", StreamingSpeechBuffer(transcriber))
                    track = tracks[track_id]
                    events = await asyncio.to_thread(track.buffer.feed, pcm)
                    if track.buffer.speaking and timestamp - track.last_hint_at >= 1:
                        track.last_hint_at = timestamp
                        if hint and hint.casefold() != bot_name.casefold():
                            track.hints[hint] += 1
                        else:
                            track.ambiguous_hints += 1
                    for event in events:
                        if event.type == "speech_started":
                            track.started_at = max(0, timestamp - started)
                        elif event.type == "final_transcript" and event.text:
                            speaker = track.speaker
                            if track.hints:
                                name, count = track.hints.most_common(1)[0]
                                if count >= 2 and count / (sum(track.hints.values()) + track.ambiguous_hints) >= 0.8:
                                    speaker = name
                            alert = await asyncio.to_thread(
                                _persist_turn, meeting_id, speaker,
                                track.started_at if track.started_at is not None else max(0, timestamp - started - 1),
                                max(0, timestamp - started), event.text, event.language, recent, client,
                            )
                            if alert:
                                pending_questions.append((time.time(), alert))
                            elif pending_questions:
                                # A response occurred; avoid labeling the earlier question unanswered.
                                pending_questions.clear()
                            track.started_at = None
                            track.hints.clear()
                            track.ambiguous_hints = 0
                for track in tracks.values():
                    for event in await asyncio.to_thread(track.buffer.flush):
                        if event.type == "final_transcript" and event.text:
                            await asyncio.to_thread(_persist_turn, meeting_id, track.speaker,
                                                    track.started_at if track.started_at is not None else 0,
                                                    time.time() - started, event.text, event.language, recent, client)
            finally:
                stopping.set()
                await speaker_task
            if dropped:
                logger.warning("Native bot dropped %s PCM frames meeting=%s", dropped, meeting_id)
        finally:
            try:
                try:
                    if await has_google_session(context):
                        await save_auth_state(context, folder)
                finally:
                    await context.close()
            finally:
                if console is not None:
                    console.__exit__(None, None, None)
                profile_lock.__exit__(None, None, None)


@celery_app.task(name="run_native_meeting_bot", bind=True)
def run_native_meeting_bot_task(self, meeting_id: str, meeting_url: str, bot_name: str = "MeetPilot AI") -> None:
    ident = uuid.UUID(meeting_id)
    client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
    lock_key = f"native-meeting:{ident}:lock"
    token = uuid.uuid4().hex
    if not client.set(lock_key, token, nx=True, ex=7200):
        logger.warning("Native meeting bot already running meeting=%s", ident)
        return
    try:
        target = parse_meeting_target(meeting_url)
        asyncio.run(run_native_meeting_bot(ident, target, bot_name, client, token))
    except Exception as exc:
        message = (f"[{exc.code}] {exc}" if isinstance(exc, MeetingJoinError)
                   else f"Local bot failed: {type(exc).__name__}: {str(exc)[:300]}")
        payload = {"kind": "bot_status", "state": "failed", "text": message,
                   "source_segment_id": "bot-status", "timestamp": 0, "speaker": "", "source_quote": ""}
        client.setex(f"native-meeting:{ident}:status", 86400, json.dumps(payload))
        _publish_insight(client, ident, payload)
        logger.exception("Native meeting bot failed meeting=%s", ident)
        with SessionLocal() as db:
            meeting = db.get(Meeting, ident)
            if meeting is not None and meeting.status == MeetingStatus.in_progress:
                meeting.status = MeetingStatus.failed
                meeting.failure_reason = (f"[{exc.code}] {exc}" if isinstance(exc, MeetingJoinError)
                                          else f"Local bot failed: {type(exc).__name__}: {str(exc)[:300]}")
                db.commit()
    finally:
        if client.get(lock_key) == token.encode():
            client.delete(lock_key)
        with SessionLocal() as db:
            meeting = db.get(Meeting, ident)
            if meeting is not None and meeting.status == MeetingStatus.queued:
                from app.workers.meeting_processor import process_live_meeting
                process_live_meeting.delay(meeting_id)
