"""Speaker-label provider boundary; local fallback does not claim distinct voices."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.app_config import APP_CONFIG


@dataclass(frozen=True)
class SpeakerTurn:
    speaker_id: str
    start_time: float
    end_time: float
    confidence: float | None = None


class DiarizationProvider(ABC):
    supports_distinct_speakers = False

    @abstractmethod
    def diarize(self, duration_seconds: float) -> list[SpeakerTurn]:
        raise NotImplementedError


class SingleSpeakerFallback(DiarizationProvider):
    def diarize(self, duration_seconds: float) -> list[SpeakerTurn]:
        if duration_seconds <= 0:
            return []
        return [SpeakerTurn("Speaker 1", 0.0, duration_seconds, None)]


def get_diarization_provider() -> DiarizationProvider:
    if APP_CONFIG.pilot.diarization_provider == "single_speaker":
        return SingleSpeakerFallback()
    raise RuntimeError("No verified local multi-speaker diarization provider is configured")
