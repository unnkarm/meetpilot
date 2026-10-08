"""Meeting-scoped Pilot state persisted in the existing Redis instance."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum

import redis

from app.core.app_config import APP_CONFIG
from app.core.config import settings


class PilotState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    WAKE_DETECTED = "WAKE_DETECTED"
    CAPTURING_QUERY = "CAPTURING_QUERY"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


_ALLOWED = {
    PilotState.IDLE: {PilotState.LISTENING},
    PilotState.LISTENING: {PilotState.WAKE_DETECTED, PilotState.ERROR, PilotState.IDLE},
    PilotState.WAKE_DETECTED: {PilotState.CAPTURING_QUERY, PilotState.PROCESSING, PilotState.ERROR, PilotState.LISTENING},
    PilotState.CAPTURING_QUERY: {PilotState.PROCESSING, PilotState.LISTENING, PilotState.ERROR},
    PilotState.PROCESSING: {PilotState.SPEAKING, PilotState.LISTENING, PilotState.ERROR},
    PilotState.SPEAKING: {PilotState.LISTENING, PilotState.CAPTURING_QUERY, PilotState.ERROR},
    PilotState.ERROR: {PilotState.LISTENING, PilotState.IDLE},
}


@dataclass
class PilotSession:
    session_id: str
    workspace_id: str
    meeting_id: str
    active_user_id: str
    state: PilotState = PilotState.IDLE
    wake_word: str = "Hey Pilot"
    current_language: str | None = None
    current_context: dict = field(default_factory=dict)
    last_queries: list[str] = field(default_factory=list)
    last_tool_results: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def transition(self, state: PilotState) -> None:
        if state not in _ALLOWED[self.state]:
            raise ValueError(f"Invalid Pilot transition {self.state.value} -> {state.value}")
        self.state = state
        self.updated_at = datetime.now(timezone.utc).isoformat()


class PilotSessionStore:
    def __init__(self, client=None):
        self.client = client or redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    @staticmethod
    def _key(session_id: str) -> str:
        return f"pilot:session:{session_id}"

    def save(self, session: PilotSession) -> None:
        self.client.setex(self._key(session.session_id), APP_CONFIG.pilot.session_ttl_seconds,
                          json.dumps(asdict(session), ensure_ascii=False))

    def start(self, workspace_id: uuid.UUID, meeting_id: uuid.UUID, user_id: uuid.UUID) -> PilotSession:
        session = PilotSession(str(uuid.uuid4()), str(workspace_id), str(meeting_id), str(user_id),
                               wake_word=APP_CONFIG.pilot.wake_word)
        session.transition(PilotState.LISTENING)
        self.save(session)
        return session

    def get(self, session_id: str, workspace_id: uuid.UUID, meeting_id: uuid.UUID, user_id: uuid.UUID) -> PilotSession | None:
        raw = self.client.get(self._key(session_id))
        if not raw:
            return None
        session = PilotSession(**json.loads(raw))
        session.state = PilotState(session.state)
        if (session.workspace_id, session.meeting_id, session.active_user_id) != (
            str(workspace_id), str(meeting_id), str(user_id)
        ):
            return None
        return session

    def stop(self, session: PilotSession) -> None:
        if session.state != PilotState.IDLE:
            if session.state != PilotState.ERROR:
                session.state = PilotState.IDLE
                session.updated_at = datetime.now(timezone.utc).isoformat()
            else:
                session.transition(PilotState.IDLE)
        self.save(session)

    def transition(self, session: PilotSession, state: PilotState) -> PilotSession:
        session.transition(state)
        self.save(session)
        return session


def public_session(session: PilotSession) -> dict:
    return {
        "session_id": session.session_id,
        "workspace_id": session.workspace_id,
        "meeting_id": session.meeting_id,
        "active_user_id": session.active_user_id,
        "state": session.state.value,
        "wake_word": session.wake_word,
        "current_language": session.current_language,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
