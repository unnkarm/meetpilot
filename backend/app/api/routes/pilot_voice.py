"""Authenticated local Pilot voice session and PCM16 WebSocket transport."""

import asyncio
import json
import logging
import re
import uuid
import redis

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_meeting_for_member
from app.core.app_config import APP_CONFIG
from app.core.config import settings
from app.core.security import verify_clerk_token
from app.database.session import SessionLocal, get_db
from app.models.user import User
from app.models.meeting import MeetingStatus
from app.models.workspace import Workspace
from app.services.pilot_audio import WebSocketAudioProvider
from app.services.vexa_audio_provider import VexaMeetingAudioProvider
from app.services.pilot_observability import PilotTrace
from app.services.pilot_runtime import execute_pilot_query, route_intent
from app.services.pilot_session import PilotSessionStore, PilotState, public_session
from app.services.pilot_streaming_stt import SpeechEvent, StreamingSpeechBuffer, get_stt_provider, MeetingLanguageSTT
from app.services.pilot_tts import get_tts_provider, synthesize_wake_ack
from app.services.pilot_wakeword import get_wakeword_provider, WakeGate
from app.services.pilot_language import is_addressed_followup, reply_language, localized_message

router = APIRouter(prefix="/api/v1/meetings", tags=["pilot"])
logger = logging.getLogger(__name__)


def _live_bot_audio_available(meeting) -> bool:
    return meeting.source == "live" and meeting.status == MeetingStatus.in_progress


def _query_key(text: str) -> str:
    """Compare repeat utterances while a reply is still being generated."""
    return " ".join(re.findall(r"\w+", text.casefold(), re.UNICODE))


def _followup_is_addressed(text: str, source: str) -> bool:
    if source == "microphone":
        return bool(text.strip())
    # A call contains ordinary conversation. A recognized participant can ask
    # follow-up questions without another wake, but a nearby statement should
    # not turn the assistant into a meeting participant without being asked.
    return is_addressed_followup(text) or bool(re.search(
        r"^(?:and\s+|but\s+|so\s+)?(?:what|why|when|where|who|which|how|can\s+you|"
        r"could\s+you|would\s+you|do\s+you|did\s+we|are\s+there|is\s+there|tell\s+me|"
        r"give\s+me|summari[sz]e|explain|repeat|say\s+that|make\s+(?:it|that)|"
        r"go\s+on|continue|more\s+detail|shorter|yes\b|no\b)", text.strip(), re.I))


def _history_for_turn(session, source: str, speaker: str | None) -> list[dict]:
    key = "microphone" if source == "microphone" else WakeGate.normalize_speaker(speaker)
    if key is None or session.dialogue_speaker != key:
        return []
    return [{"role": turn["role"], "content": turn["content"][:2000]}
            for turn in session.conversation_history[-6:]
            if turn.get("role") in {"user", "assistant"} and isinstance(turn.get("content"), str)]


def _session_for_member(meeting_id: uuid.UUID, session_id: str, user: User, db: Session):
    meeting = get_meeting_for_member(meeting_id, user, db)
    session = PilotSessionStore().get(session_id, meeting.workspace_id, meeting.id, user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="Pilot session not found")
    return meeting, session


@router.post("/{meeting_id}/pilot/sessions")
def start_pilot_session(meeting_id: uuid.UUID, current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> dict:
    if not APP_CONFIG.pilot.enabled:
        raise HTTPException(status_code=503, detail="Pilot is disabled")
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    return public_session(PilotSessionStore().start(meeting.workspace_id, meeting.id, current_user.id))


@router.get("/{meeting_id}/pilot/sessions/{session_id}")
def get_pilot_session(meeting_id: uuid.UUID, session_id: str,
                      current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    _, session = _session_for_member(meeting_id, session_id, current_user, db)
    return public_session(session)


@router.delete("/{meeting_id}/pilot/sessions/{session_id}")
def stop_pilot_session(meeting_id: uuid.UUID, session_id: str,
                       current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    _, session = _session_for_member(meeting_id, session_id, current_user, db)
    store = PilotSessionStore()
    store.stop(session)
    return public_session(session)


async def _play_text(websocket, meeting, text, playback_ack, ack_state, *, wake_ack=False, language=None):
    def selected_voice():
        with SessionLocal() as voice_db:
            workspace = voice_db.get(Workspace, meeting.workspace_id)
            return workspace.pilot_voice_id if workspace else "lessac"
    voice_id = await asyncio.to_thread(selected_voice)
    if _live_bot_audio_available(meeting):
        await VexaMeetingAudioProvider(meeting.id, meeting.workspace_id).speak_text(text, voice_id, language=language)
        return
    async def chunks():
        if wake_ack:
            yield await synthesize_wake_ack(voice_id)
        else:
            async for wav in get_tts_provider(voice_id).synthesize_chunks(text, language):
                yield wav
    provider = WebSocketAudioProvider(websocket)
    async for wav in chunks():
        interaction_id = uuid.uuid4().hex
        ack_state["expected"] = interaction_id
        ack_state["error"] = None
        playback_ack.clear()
        await provider.speak(wav, interaction_id=interaction_id)
        await asyncio.wait_for(playback_ack.wait(), timeout=45)
        ack_state["expected"] = None
        if ack_state.get("error"):
            raise RuntimeError(ack_state["error"])


async def _acknowledge_wake(websocket, meeting, playback_ack, ack_state):
    await websocket.send_json({"type": "wake_acknowledged", "text": "Yes sir."})
    if APP_CONFIG.pilot.tts_enabled:
        try:
            await _play_text(websocket, meeting, "Yes sir.", playback_ack, ack_state, wake_ack=True)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Pilot wake acknowledgement failed meeting=%s", meeting.id)
            await websocket.send_json({"type": "error", "detail": "Pilot heard you, but could not play its acknowledgement."})


async def _handle_final(websocket: WebSocket, db: Session, meeting, user, session, store,
                        text: str, language: str | None, playback_ack: asyncio.Event,
                        ack_state: dict, *, allow_actions: bool = True, wake_ack_task=None,
                        captured_query: bool = False, conversation_history=None,
                        dialogue_speaker=None) -> bool:
    if session.state in {PilotState.SPEAKING, PilotState.PROCESSING, PilotState.IDLE}:
        return False
    wake = get_wakeword_provider()
    trace = PilotTrace(meeting.id, meeting.workspace_id)
    with trace.stage("wake_detection"):
        if captured_query:
            query = text.strip()
        elif session.state == PilotState.CAPTURING_QUERY:
            detected = wake.detect(text)
            query = detected if detected is not None else text.strip()
        else:
            query = wake.detect(text)
            if query is None:
                return False
            store.transition(session, PilotState.WAKE_DETECTED)
            await websocket.send_json({"type": "wake_detected", "session": public_session(session)})
            if not query:
                store.transition(session, PilotState.CAPTURING_QUERY)
                return False
    if not query:
        return False
    if session.state != PilotState.CAPTURING_QUERY and session.state != PilotState.WAKE_DETECTED:
        return False
    store.transition(session, PilotState.PROCESSING)
    session.current_language = language
    store.save(session)
    await websocket.send_json({"type": "state", "session": public_session(session)})
    try:
        with trace.stage("response_total"):
            # SQLAlchemy sessions belong to the thread that uses them. Voice
            # I/O stays on the event loop while retrieval runs in a worker.
            def run_query():
                with SessionLocal() as query_db:
                    query_user = query_db.get(User, user.id)
                    return execute_pilot_query(
                        query_db, meeting.id, meeting.workspace_id, query_user,
                        query, session.wake_word, trace,
                        conversation_history=conversation_history,
                    )

            if not allow_actions and route_intent(query) == "action_request":
                result = {"intent": "action_request", "answer": localized_message("unverified_voice", query, "[Uncertain: Meeting voices are not verified workspace identities. Use your microphone or the task form to create this task.]"), "citations": []}
            else:
                result = await asyncio.to_thread(run_query)
            result["reply_language"] = reply_language(query, language)
            fresh = store.get(session.session_id, meeting.workspace_id, meeting.id, user.id)
            if fresh is None or fresh.state == PilotState.IDLE:
                return False
            session.last_queries = (session.last_queries + [query])[-5:]
            session.dialogue_speaker = dialogue_speaker
            session.conversation_history = (
                list(conversation_history or []) + [{"role": "user", "content": query[:2000]},
                    {"role": "assistant", "content": str(result.get("answer") or "")[:2000]}]
            )[-6:]
            session.last_tool_results = (session.last_tool_results + [{"intent": result["intent"]}])[-5:]
            store.save(session)
            await websocket.send_json({"type": "answer", **result})
            if APP_CONFIG.pilot.tts_enabled and result.get("answer"):
                # Recognition/retrieval already ran while the quick acknowledgement
                # played. Serialize only speech output to avoid overlapping voices.
                if wake_ack_task is not None:
                    await asyncio.gather(wake_ack_task, return_exceptions=True)
                store.transition(session, PilotState.SPEAKING)
                await websocket.send_json({"type": "state", "session": public_session(session)})
                with trace.stage("tts_and_audio_output"):
                    await _play_text(websocket, meeting, result.get("speech_text", result["answer"]),
                                     playback_ack, ack_state, language=result["reply_language"])
        if session.state in {PilotState.PROCESSING, PilotState.SPEAKING}:
            store.transition(session, PilotState.LISTENING)
            await websocket.send_json({"type": "state", "session": public_session(session)})
        return True
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Pilot interaction failed meeting=%s session=%s", meeting.id, session.session_id)
        if session.state != PilotState.ERROR:
            store.transition(session, PilotState.ERROR)
        await websocket.send_json({"type": "error", "detail": str(exc)[:200], "session": public_session(session)})
        store.transition(session, PilotState.LISTENING)
        await websocket.send_json({"type": "state", "session": public_session(session)})
        return False


@router.websocket("/{meeting_id}/pilot/audio")
async def pilot_audio(websocket: WebSocket, meeting_id: uuid.UUID):
    await websocket.accept()
    db = SessionLocal()
    try:
        # Browser WebSocket cannot set Authorization headers. Authenticate in the first frame.
        hello = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        token = hello.get("token", "") if isinstance(hello, dict) else ""
        claims = verify_clerk_token(token) if isinstance(token, str) else None
        if not claims or not claims.get("sub"):
            await websocket.close(code=1008)
            return
        user = db.query(User).filter(User.clerk_id == claims["sub"]).one_or_none()
        if user is None:
            await websocket.close(code=1008)
            return
        meeting = get_meeting_for_member(meeting_id, user, db)
        store = PilotSessionStore()
        session = store.get(str(hello.get("session_id", "")), meeting.workspace_id, meeting.id, user.id)
        if session is None or session.state == PilotState.IDLE:
            await websocket.close(code=1008)
            return
        source = hello.get("input_source", "microphone")
        if source not in {"microphone", "meeting"} or (source == "meeting" and not _live_bot_audio_available(meeting)):
            await websocket.close(code=1008)
            return
        transcriber = MeetingLanguageSTT(get_stt_provider(), getattr(meeting, "transcription_language", None))
        buffer = StreamingSpeechBuffer(transcriber)
        track_buffers = {}
        incoming = asyncio.Queue(maxsize=512)

        async def pump_client():
            try:
                while True:
                    await incoming.put(await websocket.receive())
            except WebSocketDisconnect:
                await incoming.put({"type": "websocket.disconnect"})

        async def pump_bot():
            client = redis.Redis.from_url(settings.REDIS_URL)
            sub = client.pubsub(ignore_subscribe_messages=True)
            sub.subscribe(f"native-meeting:{meeting_id}:tts-events")
            if source == "meeting":
                sub.subscribe(f"native-meeting:{meeting_id}:transcript")
            try:
                while True:
                    message = await asyncio.to_thread(sub.get_message, timeout=0.1)
                    if not message:
                        continue
                    if message["channel"].endswith(b":transcript"):
                        await incoming.put({"text": json.dumps({"type": "vexa_transcript", "event": json.loads(message["data"])})})
                    else:
                        data = json.loads(message["data"])
                        if data.get("type") == "pilot_interrupted":
                            await incoming.put({"text": '{"type":"native_interrupted"}'})
            finally:
                sub.close()
                client.close()

        pumps = [asyncio.create_task(pump_client())]
        async def watch_session():
            while True:
                await asyncio.sleep(1)
                await incoming.put({"text": '{"type":"session_tick"}'})
        pumps.append(asyncio.create_task(watch_session()))
        if meeting.source == "live":
            pumps.append(asyncio.create_task(pump_bot()))
        playback_ack = asyncio.Event()
        ack_state: dict[str, str | None] = {"expected": None}
        active_response: asyncio.Task | None = None
        wake_ack_task: asyncio.Task | None = None
        wake_gate = WakeGate()
        microphone_turn = 0
        processed_turns = []
        active_query = ""
        response_generation = 0
        pending_turn = None
        # Reconnecting opens a new listening interaction. Never feed a previous
        # participant's questions into a newly connected meeting voice source.
        session.conversation_history = []
        session.dialogue_speaker = None

        def start_response(event, query):
            nonlocal active_response, active_query, response_generation
            if session.state == PilotState.LISTENING:
                store.transition(session, PilotState.WAKE_DETECTED)
                store.transition(session, PilotState.CAPTURING_QUERY)
            if session.state not in {PilotState.CAPTURING_QUERY, PilotState.WAKE_DETECTED}:
                return
            response_generation += 1
            generation = response_generation
            active_query = _query_key(query)
            history = _history_for_turn(session, source, event.speaker)
            speaker_key = "microphone" if source == "microphone" else WakeGate.normalize_speaker(event.speaker)
            wake_gate.arm_interrupt(event.speaker if source == "meeting" else None)
            acknowledgement = wake_ack_task

            async def respond():
                completed = False
                cancelled = False
                try:
                    completed = await _handle_final(
                        websocket, db, meeting, user, session, store, query, event.language,
                        playback_ack, ack_state, allow_actions=source != "meeting",
                        wake_ack_task=acknowledgement, captured_query=True,
                        conversation_history=history, dialogue_speaker=speaker_key,
                    )
                except asyncio.CancelledError:
                    cancelled = True
                    raise
                finally:
                    completion = {"type": "pilot.response.done", "generation": generation,
                                  "completed": completed, "speaker": event.speaker}
                    if cancelled:
                        # Shutdown/barge-in must not wait on a full transport queue.
                        try:
                            incoming.put_nowait(completion)
                        except asyncio.QueueFull:
                            pass
                    else:
                        await incoming.put(completion)
            active_response = asyncio.create_task(respond())

        async def interrupt_playback(speaker=None):
            nonlocal active_response, wake_ack_task, response_generation, active_query, pending_turn
            ack_state["expected"] = None
            tasks = []
            if wake_ack_task and not wake_ack_task.done():
                wake_ack_task.cancel()
                tasks.append(wake_ack_task)
            if session.state == PilotState.SPEAKING:
                if active_response and not active_response.done():
                    active_response.cancel()
                    tasks.append(active_response)
                response_generation += 1
                active_response = None
                active_query = ""
                pending_turn = None
                store.transition(session, PilotState.CAPTURING_QUERY)
            wake_gate.arm_interrupt(speaker or wake_gate.speaker)
            await websocket.send_json({"type": "pilot_interrupted", "session": public_session(session)})
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            # Vexa's cancelled speak operation stops and joins its own playback
            # before releasing the lock. A second late stop could kill the next
            # response which has just acquired that lock.
            if meeting.source == "live" and not tasks:
                try:
                    await VexaMeetingAudioProvider(meeting.id, meeting.workspace_id).interrupt()
                except Exception:
                    logger.exception("Could not stop Pilot audio meeting=%s", meeting.id)

        await websocket.send_json({"type": "ready", "format": "pcm_s16le", "sample_rate": APP_CONFIG.pilot.audio_sample_rate,
                                   "channels": 1, "session": public_session(session)})
        while True:
            frame = await incoming.get()
            if frame.get("type") == "websocket.disconnect":
                break
            # Refresh to observe a stop issued through HTTP or another connection.
            fresh = store.get(session.session_id, meeting.workspace_id, meeting.id, user.id)
            if fresh is None or fresh.state == PilotState.IDLE:
                await websocket.close(code=1000)
                break
            if frame.get("type") == "pilot.response.done":
                if frame["generation"] != response_generation:
                    continue
                active_response = None
                active_query = ""
                if not frame["completed"] and session.state in {PilotState.PROCESSING, PilotState.SPEAKING}:
                    # An upstream playback interruption can cancel speak_text
                    # without a locally initiated barge-in. Release the state too.
                    store.transition(session, PilotState.LISTENING)
                    await websocket.send_json({"type": "state", "session": public_session(session)})
                if frame["completed"]:
                    wake_gate.open_followup(frame.get("speaker"), allow_unlabelled=source == "microphone")
                if pending_turn is not None:
                    event, query = pending_turn
                    pending_turn = None
                    start_response(event, query)
                continue
            if frame.get("bytes") is not None:
                if source == "meeting" and "track_id" not in frame:
                    continue
                if "track_id" in frame:
                    track_id = frame["track_id"]
                    if track_id not in track_buffers:
                        if len(track_buffers) >= 32:
                            continue
                        track_buffers[track_id] = StreamingSpeechBuffer(transcriber)
                    buffer = track_buffers[track_id]
                try:
                    # The first voiced frame returns a barge-in event before any
                    # partial Whisper transcription is due.
                    events = await asyncio.to_thread(
                        buffer.feed, frame["bytes"], assistant_speaking=(session.state == PilotState.SPEAKING
                            or (wake_ack_task is not None and not wake_ack_task.done())),
                    )
                except ValueError:
                    await websocket.send_json({"type": "error", "detail": "Invalid PCM16 frame"})
                    continue
                except Exception:
                    logger.exception("Pilot STT failed meeting=%s session=%s", meeting.id, session.session_id)
                    buffer.reset()
                    store.transition(session, PilotState.ERROR)
                    await websocket.send_json({"type": "error", "detail": "Local speech recognition is unavailable"})
                    store.transition(session, PilotState.LISTENING)
                    continue
            else:
                try:
                    data = json.loads(frame.get("text") or "{}")
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "vexa_transcript":
                    turn = data.get("event") or {}
                    if turn.get("utterance_id") in processed_turns:
                        continue
                    events = [SpeechEvent(turn.get("type", "partial_transcript"), turn.get("text", ""),
                                          turn.get("language"), turn.get("speaker"), turn.get("confidence"),
                                          turn.get("utterance_id"))]
                    if turn.get("text", "").strip() and (session.state == PilotState.SPEAKING
                            or (wake_ack_task and not wake_ack_task.done())):
                        events.insert(0, SpeechEvent("pilot_interrupted", speaker=turn.get("speaker")))
                elif data.get("type") == "native_interrupted":
                    events = [SpeechEvent("pilot_interrupted")]
                elif data.get("type") in {"playback_complete", "playback_failed"}:
                    if data.get("interaction_id") == ack_state["expected"]:
                        if data["type"] == "playback_failed":
                            ack_state["error"] = "The browser could not play Pilot audio. Enable audio playback and retry."
                        playback_ack.set()
                    continue
                else:
                    if data.get("type") == "session_tick":
                        # Membership revocation must close existing sockets too.
                        db.expire_all()
                        get_meeting_for_member(meeting_id, user, db)
                        if not wake_gate.accepts(wake_gate.speaker) and session.state in {
                            PilotState.LISTENING, PilotState.CAPTURING_QUERY,
                        }:
                            session.conversation_history = []
                            session.dialogue_speaker = None
                            if session.state == PilotState.CAPTURING_QUERY:
                                store.transition(session, PilotState.LISTENING)
                                await websocket.send_json({"type": "state", "session": public_session(session)})
                            wake_gate.disarm()
                        continue
                    if data.get("type") != "flush":
                        continue
                    try:
                        events = await asyncio.to_thread(buffer.flush)
                    except Exception:
                        logger.exception("Pilot STT flush failed meeting=%s session=%s", meeting.id, session.session_id)
                        buffer.reset()
                        store.transition(session, PilotState.ERROR)
                        await websocket.send_json({"type": "error", "detail": "Local speech recognition is unavailable"})
                        store.transition(session, PilotState.LISTENING)
                        continue
            for event in events:
                if event.type == "speech_started":
                    microphone_turn += 1
                if event.type == "pilot_interrupted":
                    if session.state == PilotState.SPEAKING or (wake_ack_task and not wake_ack_task.done()):
                        await interrupt_playback(event.speaker)
                    continue
                if event.type in {"partial_transcript", "final_transcript"}:
                    speaker = event.speaker if source == "meeting" else None
                    turn_id = event.utterance_id or (f"mic:{microphone_turn}" if source == "microphone" else None)
                    if turn_id and turn_id in processed_turns:
                        continue
                    previously_armed = wake_gate.accepts(speaker)
                    conversational_followup = (previously_armed and wake_gate.followup
                                               and _followup_is_addressed(event.text, source))
                    woke = wake_gate.observe(
                        event.text, final=event.type == "final_transcript",
                        utterance_id=turn_id, speaker=speaker, confidence=event.confidence,
                    )
                    if woke:
                        if not previously_armed:
                            session.conversation_history = []
                            session.dialogue_speaker = None
                        if session.state == PilotState.LISTENING:
                            store.transition(session, PilotState.WAKE_DETECTED)
                            store.transition(session, PilotState.CAPTURING_QUERY)
                        await websocket.send_json({"type": "wake_detected", "session": public_session(session)})
                        # A repeat while Qwen is thinking must not cancel the answer
                        # or start a second overlapping acknowledgement.
                        if active_response is None and (wake_ack_task is None or wake_ack_task.done()):
                            wake_ack_task = asyncio.create_task(_acknowledge_wake(websocket, meeting, playback_ack, ack_state))
                    elif conversational_followup and session.state == PilotState.LISTENING:
                        store.transition(session, PilotState.WAKE_DETECTED)
                        store.transition(session, PilotState.CAPTURING_QUERY)
                        await websocket.send_json({"type": "query_received", "text": event.text,
                                                   "session": public_session(session)})
                    addressed = wake_gate.accepts(speaker) and (
                        not wake_gate.followup or conversational_followup or woke
                    )
                    if addressed and event.type == "partial_transcript":
                        wake_gate.extend_capture()
                await websocket.send_json({"type": event.type, "text": event.text, "language": event.language,
                                           "speaker": event.speaker, "confidence": event.confidence})
                if event.type == "final_transcript":
                    if not addressed or session.state == PilotState.IDLE:
                        continue
                    detected = wake_gate.provider.detect(event.text)
                    query = event.text.strip() if detected is None else detected
                    if turn_id:
                        processed_turns = (processed_turns + [turn_id])[-64:]
                    if not query:
                        continue
                    try:
                        if active_response is not None:
                            if _query_key(query) == active_query or (pending_turn is not None
                                    and _query_key(query) == _query_key(pending_turn[1])):
                                continue
                            pending_turn = (event, query)
                            await websocket.send_json({"type": "query_queued", "text": query})
                            continue
                        await websocket.send_json({"type": "query_received", "text": query})
                        start_response(event, query)
                    except Exception:
                        db.rollback()
                        logger.exception("Pilot wake processing failed meeting=%s session=%s", meeting.id, session.session_id)
                        store.transition(session, PilotState.ERROR)
                        await websocket.send_json({"type": "error", "detail": "Pilot could not process the query"})
                        store.transition(session, PilotState.LISTENING)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except HTTPException:
        await websocket.close(code=1008)
    finally:
        if "wake_ack_task" in locals() and wake_ack_task and not wake_ack_task.done():
            wake_ack_task.cancel()
            await asyncio.gather(wake_ack_task, return_exceptions=True)
        for task in locals().get("pumps", []):
            task.cancel()
        if "pumps" in locals():
            await asyncio.gather(*pumps, return_exceptions=True)
        if "active_response" in locals() and active_response and not active_response.done():
            active_response.cancel()
            await asyncio.gather(active_response, return_exceptions=True)
        if "session" in locals() and "store" in locals():
            store.stop(session)
        db.close()
