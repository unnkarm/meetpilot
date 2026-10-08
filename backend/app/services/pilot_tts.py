"""Offline neural speech synthesis with bounded, browser-safe WAV chunks."""

import asyncio
import audioop
import io
import logging
import os
import re
import threading
import textwrap
import wave
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from app.core.app_config import APP_CONFIG

logger = logging.getLogger(__name__)
_VOICE_LOCK = threading.Lock()
_DEFAULT_VOICE = Path("/app/voices/en_US-lessac-medium.onnx")
VOICE_MODELS = {"lessac": ("Lessac · US English", "en_US-lessac-medium.onnx"),
                "ryan": ("Ryan · US English", "en_US-ryan-medium.onnx")}


def voice_path(voice_id: str) -> Path:
    if voice_id not in VOICE_MODELS:
        raise ValueError("Unknown local voice")
    if voice_id == "lessac":
        return Path(os.getenv("PILOT_PIPER_VOICE_PATH", str(_DEFAULT_VOICE)))
    return Path(os.getenv("PILOT_VOICES_DIR", "/app/voices")) / VOICE_MODELS[voice_id][1]


def available_voices() -> list[dict]:
    return [{"id": ident, "label": details[0], "available": voice_path(ident).is_file()
             and voice_path(ident).with_suffix(".onnx.json").is_file()} for ident, details in VOICE_MODELS.items()]


def require_voice(voice_id: str) -> str:
    if not any(v["id"] == voice_id and v["available"] for v in available_voices()):
        raise ValueError("The selected local voice is not installed")
    return voice_id


def parse_voice_token(token: str) -> str:
    # The private Vexa transport carries the voice and playback correlation ID
    # together. Old UUID-only clients and the diagnostic smoke test use default.
    if token.startswith("mp/"):
        parts = token.split("/")
        if len(parts) != 3 or parts[1] not in VOICE_MODELS or not re.fullmatch(r"[a-f0-9]{32}", parts[2]):
            raise ValueError("Invalid voice token")
        return parts[1]
    if token in VOICE_MODELS:
        return token
    return "lessac"


def _wav(pcm: bytes, sample_rate: int) -> bytes:
    if sample_rate not in (16000, 24000) or not pcm or len(pcm) % 2:
        raise ValueError("Expected nonempty PCM16 at 16 or 24 kHz")
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(pcm)
    return output.getvalue()


def _repack(source: bytes, sample_rate: int) -> bytes:
    try:
        with wave.open(io.BytesIO(source), "rb") as reader:
            if reader.getsampwidth() != 2:
                raise ValueError("Only PCM16 WAV is supported")
            pcm = reader.readframes(reader.getnframes())
            if reader.getnchannels() != 1:
                pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
            if reader.getframerate() != sample_rate:
                pcm, _ = audioop.ratecv(pcm, 2, 1, reader.getframerate(), sample_rate, None)
    except (wave.Error, EOFError) as exc:
        raise RuntimeError("Local TTS produced invalid WAV") from exc
    return _wav(pcm, sample_rate)


def _sentences(text: str) -> list[str]:
    content = " ".join(text.strip().split())[:3000]
    if not content:
        raise ValueError("TTS text is empty")
    return [chunk for part in re.split(r"(?<=[.!?])\s+", content) if part
            for chunk in textwrap.wrap(part, width=240, break_long_words=True,
                                       break_on_hyphens=False)]


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize_chunks(self, text: str, language: str | None = None,
                                sample_rate: int = 24000) -> AsyncIterator[bytes]:
        """Yield independently playable PCM16 mono WAV chunks."""

    async def synthesize(self, text: str, language: str | None = None,
                         sample_rate: int = 24000) -> bytes:
        chunks = []
        async for chunk in self.synthesize_chunks(text, language, sample_rate):
            with wave.open(io.BytesIO(chunk), "rb") as reader:
                chunks.append(reader.readframes(reader.getnframes()))
        return _wav(b"".join(chunks), sample_rate)


class EspeakNGTTS(TTSProvider):
    async def synthesize_chunks(self, text: str, language: str | None = None,
                                sample_rate: int = 24000) -> AsyncIterator[bytes]:
        voice = (language or "en").split("-")[0].lower()
        if not voice.isalpha() or len(voice) > 3:
            voice = "en"
        for sentence in _sentences(text):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "espeak-ng", "--stdout", "-v", voice, sentence,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("Local espeak-ng is unavailable") from exc
            try:
                output, error = await asyncio.wait_for(proc.communicate(), timeout=30)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                proc.kill()
                await proc.communicate()
                raise
            if proc.returncode or not output:
                raise RuntimeError(f"Local TTS failed: {error.decode(errors='replace')[:200]}")
            yield _repack(output, sample_rate)


@lru_cache(maxsize=2)
def _load_voice(model_path: str):
    from piper import PiperVoice
    return PiperVoice.load(model_path)


def _piper_sentence(model_path: str, sentence: str, sample_rate: int) -> bytes:
    with _VOICE_LOCK:
        voice = _load_voice(model_path)
        pcm_parts = []
        rate_state = None
        for chunk in voice.synthesize(sentence):
            if chunk.sample_width != 2:
                raise RuntimeError("Piper produced non-PCM16 audio")
            pcm = chunk.audio_int16_bytes
            if chunk.sample_channels != 1:
                pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
            if chunk.sample_rate != sample_rate:
                pcm, rate_state = audioop.ratecv(pcm, 2, 1, chunk.sample_rate,
                                                 sample_rate, rate_state)
            pcm_parts.append(pcm)
    return _wav(b"".join(pcm_parts), sample_rate)


class PiperTTS(TTSProvider):
    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path or os.getenv("PILOT_PIPER_VOICE_PATH", str(_DEFAULT_VOICE)))

    async def synthesize_chunks(self, text: str, language: str | None = None,
                                sample_rate: int = 24000) -> AsyncIterator[bytes]:
        if sample_rate not in (16000, 24000):
            raise ValueError("TTS sample rate must be 16000 or 24000")
        if language and language.split("-")[0].lower() != "en":
            raise RuntimeError(f"Bundled Piper voice does not support language {language}")
        if not self.model_path.is_file() or not self.model_path.with_suffix(".onnx.json").is_file():
            raise RuntimeError(f"Local Piper voice is missing: {self.model_path}")
        for sentence in _sentences(text):
            yield await asyncio.to_thread(_piper_sentence, str(self.model_path), sentence, sample_rate)


class FallbackTTS(TTSProvider):
    def __init__(self, primary: TTSProvider, fallback: TTSProvider):
        self.primary, self.fallback = primary, fallback

    async def synthesize_chunks(self, text: str, language: str | None = None,
                                sample_rate: int = 24000) -> AsyncIterator[bytes]:
        emitted = False
        try:
            async for chunk in self.primary.synthesize_chunks(text, language, sample_rate):
                emitted = True
                yield chunk
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            if emitted:
                raise
            logger.exception("Neural TTS unavailable; using local espeak-ng fallback")
        async for chunk in self.fallback.synthesize_chunks(text, language, sample_rate):
            yield chunk


def get_tts_provider(voice_id: str = "lessac") -> TTSProvider:
    provider = APP_CONFIG.pilot.tts_provider
    if provider == "piper":
        return FallbackTTS(PiperTTS(voice_path(voice_id)), EspeakNGTTS())
    if provider == "espeak_ng":
        return EspeakNGTTS()
    raise RuntimeError("Unsupported Pilot TTS provider")


@lru_cache(maxsize=4)
def _wake_ack_wav(voice_id: str, sample_rate: int) -> bytes:
    return _piper_sentence(str(voice_path(voice_id)), "Yes sir.", sample_rate)


async def synthesize_wake_ack(voice_id: str = "lessac", sample_rate: int = 24000) -> bytes:
    if APP_CONFIG.pilot.tts_provider == "piper":
        try:
            return await asyncio.to_thread(_wake_ack_wav, voice_id, sample_rate)
        except Exception:
            logger.exception("Cached neural wake acknowledgement unavailable")
    return await get_tts_provider(voice_id).synthesize("Yes sir.", sample_rate=sample_rate)
