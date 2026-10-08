"""Content-free timing events for the available Pilot backend stages."""

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from app.core.app_config import APP_CONFIG

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PilotTrace:
    meeting_id: uuid.UUID
    workspace_id: uuid.UUID
    interaction_id: uuid.UUID = field(default_factory=uuid.uuid4)
    session_id: uuid.UUID | None = None

    def event(self, name: str, status: str, latency_ms: float) -> None:
        if not APP_CONFIG.pilot.observability_enabled:
            return
        logger.info(
            "pilot_event interaction_id=%s session_id=%s workspace_id=%s meeting_id=%s event=%s status=%s latency_ms=%.2f",
            self.interaction_id, self.session_id or "none", self.workspace_id,
            self.meeting_id, name, status, latency_ms,
        )

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        except Exception:
            self.event(name, "error", (time.perf_counter() - start) * 1000)
            raise
        else:
            self.event(name, "ok", (time.perf_counter() - start) * 1000)
