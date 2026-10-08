"""Private, OpenAI-compatible local audio services used by the Vexa engine."""
import asyncio
import io
import secrets
import threading
import wave
from functools import lru_cache

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.app_config import APP_CONFIG
from app.core.config import settings
from app.services.pilot_streaming_stt import LocalWhisperSTT
from app.services.pilot_tts import get_tts_provider, parse_voice_token, synthesize_wake_ack

router = APIRouter(prefix="/internal/vexa", include_in_schema=False)
_inference_slots = asyncio.Semaphore(2)
_model_lock = threading.Lock()


def authorize(provided: str | None, expected: str) -> None:
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid audio service credential")


@lru_cache(maxsize=1)
def transcriber():
    return LocalWhisperSTT()


def transcribe_wav(raw: bytes, language: str | None) -> dict:
    try:
        with wave.open(io.BytesIO(raw), "rb") as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000):
                raise ValueError("Expected PCM16 mono WAV at 16000Hz")
            duration = wav.getnframes() / 16000
            if not 0 < duration <= 120:
                raise ValueError("Audio must contain between 0 and 120 seconds")
    except (wave.Error, EOFError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with _model_lock:
        provider = transcriber()
        if provider.model is None:
            from faster_whisper import WhisperModel
            provider.model = WhisperModel(APP_CONFIG.transcription.model, device="cpu", compute_type="int8",
                                          local_files_only=True)
        segments, info = provider.model.transcribe(io.BytesIO(raw), language=language, beam_size=1,
                                                   word_timestamps=True, vad_filter=True)
        rows = []
        words = []
        for segment in segments:
            row_words = [{"word": word.word, "start": word.start, "end": word.end}
                         for word in segment.words or []]
            words.extend(row_words)
            rows.append({"id": segment.id, "start": segment.start, "end": segment.end,
                         "text": segment.text, "avg_logprob": segment.avg_logprob,
                         "no_speech_prob": segment.no_speech_prob, "compression_ratio": segment.compression_ratio,
                         "words": row_words})
        return {"text": " ".join(row["text"].strip() for row in rows), "language": info.language,
                "duration": duration, "segments": rows, "words": words}


@router.post("/v1/audio/transcriptions")
async def audio_transcriptions(file: UploadFile = File(...), model: str = Form("whisper-1"),
                               response_format: str = Form("verbose_json"), language: str | None = Form(None),
                               authorization: str | None = Header(None)):
    authorize(authorization.removeprefix("Bearer ") if authorization else None, settings.VEXA_STT_TOKEN)
    raw = await file.read(4_000_001)
    await file.close()
    if len(raw) > 4_000_000:
        raise HTTPException(status_code=413, detail="Audio chunk exceeds 4MB")
    if response_format not in {"json", "verbose_json"}:
        raise HTTPException(status_code=422, detail="Use json or verbose_json")
    async with _inference_slots:
        return await asyncio.to_thread(transcribe_wav, raw, language)


class SpeechRequest(BaseModel):
    input: str = Field(min_length=1, max_length=6000)
    response_format: str = "pcm"
    model: str = "tts-1"
    voice: str = "auto"


@router.post("/v1/audio/speech")
async def audio_speech(payload: SpeechRequest, x_api_key: str | None = Header(None)):
    authorize(x_api_key, settings.VEXA_TTS_TOKEN)
    if payload.response_format != "pcm":
        raise HTTPException(status_code=422, detail="Vexa virtual microphone expects pcm")
    try:
        voice_id = parse_voice_token(payload.voice)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    async def stream():
        if payload.input.strip().lower().rstrip(".!?") == "yes sir":
            raw = await synthesize_wake_ack(voice_id)
            with wave.open(io.BytesIO(raw), "rb") as wav:
                yield wav.readframes(wav.getnframes())
            return
        async for raw in get_tts_provider(voice_id).synthesize_chunks(payload.input, sample_rate=24000):
            with wave.open(io.BytesIO(raw), "rb") as wav:
                yield wav.readframes(wav.getnframes())
    return StreamingResponse(stream(), media_type="application/octet-stream",
                             headers={"X-Audio-Sample-Rate": "24000", "X-Audio-Channels": "1"})
