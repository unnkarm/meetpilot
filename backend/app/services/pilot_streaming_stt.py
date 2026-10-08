"""Bounded PCM16 speech buffering and local incremental Whisper transcription."""

import audioop
import io
import wave
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

from app.core.app_config import APP_CONFIG
from app.services.pilot_diarization import get_diarization_provider


@dataclass(frozen=True)
class SpeechEvent:
    type: str
    text: str = ""
    language: str | None = None
    speaker: str | None = None
    confidence: float | None = None
    utterance_id: str | None = None


class StreamingSTTProvider(ABC):
    @abstractmethod
    def transcribe(self, pcm: bytes) -> tuple[str, str | None]:
        raise NotImplementedError


class LocalWhisperSTT(StreamingSTTProvider):
    def __init__(self):
        self.model = None
        self.lock = threading.Lock()

    def transcribe(self, pcm: bytes, language_hint: str | None = None) -> tuple[str, str | None]:
        with self.lock:
            return self._transcribe(pcm, language_hint)

    def _transcribe(self, pcm: bytes, language_hint: str | None = None) -> tuple[str, str | None]:
        from app.services.meeting_language import recognition_hint
        language = recognition_hint(language_hint)
        if self.model is None:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(APP_CONFIG.transcription.model, device="cpu", compute_type="int8",
                                      local_files_only=True)
        with io.BytesIO() as output:
            with wave.open(output, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(APP_CONFIG.pilot.audio_sample_rate)
                wav.writeframes(pcm)
            output.seek(0)
            segments, info = self.model.transcribe(output, beam_size=1, vad_filter=False, language=language, task="transcribe")
            return " ".join(segment.text.strip() for segment in segments).strip(), info.language


class MeetingLanguageSTT(StreamingSTTProvider):
    """Share one local Whisper model while keeping hints specific to each meeting."""
    def __init__(self, provider, language_hint):
        self.provider, self.language_hint = provider, language_hint

    def transcribe(self, pcm):
        return self.provider.transcribe(pcm, self.language_hint)


class StreamingSpeechBuffer:
    """Emits partials during speech and a final after silence; accepts only PCM16 mono."""

    def __init__(self, transcriber=None):
        self.transcriber = transcriber or LocalWhisperSTT()
        self.frames = bytearray()
        self.speaking = False
        self.silence_ms = 0
        self.last_partial_ms = 0
        self.last_partial = ""

    def reset(self):
        self.frames.clear()
        self.speaking = False
        self.silence_ms = 0
        self.last_partial_ms = 0
        self.last_partial = ""

    def feed(self, pcm: bytes, *, assistant_originated: bool = False,
             assistant_speaking: bool = False) -> list[SpeechEvent]:
        if assistant_originated:
            return []
        if len(pcm) % 2 or len(pcm) > APP_CONFIG.pilot.audio_sample_rate * 2:
            raise ValueError("Expected at most one second of mono 16-bit PCM")
        duration_ms = len(pcm) * 1000 // (APP_CONFIG.pilot.audio_sample_rate * 2)
        if not duration_ms:
            return []
        voiced = audioop.rms(pcm, 2) >= APP_CONFIG.pilot.vad_rms_threshold
        events = []
        if voiced and not self.speaking:
            self.speaking = True
            if assistant_speaking:
                events.append(SpeechEvent("pilot_interrupted"))
            events.append(SpeechEvent("speech_started"))
        if not self.speaking:
            return events
        self.frames.extend(pcm)
        self.silence_ms = 0 if voiced else self.silence_ms + duration_ms
        elapsed_ms = len(self.frames) * 1000 // (APP_CONFIG.pilot.audio_sample_rate * 2)
        if self.silence_ms >= APP_CONFIG.pilot.silence_end_ms or elapsed_ms >= APP_CONFIG.pilot.max_utterance_ms:
            return events + self.flush()
        if elapsed_ms - self.last_partial_ms >= APP_CONFIG.pilot.partial_interval_ms and voiced:
            self.last_partial_ms = elapsed_ms
            text, language = self.transcriber.transcribe(bytes(self.frames))
            if text and text != self.last_partial:
                self.last_partial = text
                events.append(SpeechEvent("partial_transcript", text, language))
        return events

    def flush(self) -> list[SpeechEvent]:
        if not self.speaking:
            return []
        pcm = bytes(self.frames)
        duration = len(pcm) / (APP_CONFIG.pilot.audio_sample_rate * 2)
        self.reset()
        text, language = self.transcriber.transcribe(pcm)
        turns = get_diarization_provider().diarize(duration)
        speaker = turns[0].speaker_id if turns else None
        confidence = turns[0].confidence if turns else None
        events = [SpeechEvent("speech_ended")]
        if language:
            events.append(SpeechEvent("language_detected", language=language))
        if text:
            events.append(SpeechEvent("final_transcript", text, language, speaker, confidence))
        return events


@lru_cache(maxsize=1)
def get_stt_provider():
    if APP_CONFIG.pilot.stt_provider != "faster_whisper":
        raise RuntimeError("Unsupported Pilot STT provider")
    return LocalWhisperSTT()
