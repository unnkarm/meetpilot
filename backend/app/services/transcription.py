import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict

from app.core.app_config import APP_CONFIG
from app.core.config import settings
from app.services.language_detection import detect_text_language, language_label
from app.services.audio_chunker import (
    OVERLAP_MS,
    cleanup_temp_chunks,
    dedupe_overlap_segments,
    split_audio,
)

logger = logging.getLogger(__name__)

_GEMINI_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "speaker": {"type": "string"},
                    "start_time": {"type": "number"},
                    "end_time": {"type": "number"},
                    "text": {"type": "string"},
                    "language_code": {"type": "string"},
                },
                "required": ["speaker", "start_time", "end_time", "text"],
            },
        },
        "speaker_descriptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Brief acoustic descriptions of recognized speakers (e.g. 'Speaker 1: female lead', 'Speaker 2: male engineer')",
        },
    },
    "required": ["segments"],
}

_GEMINI_SYSTEM_INSTRUCTION = (
    "You are an expert meeting transcriptionist. Listen to the provided audio and produce a "
    "complete, verbatim transcript split into short segments (one per speaker turn). "
    "Identify distinct speakers and label them consistently as 'Speaker 1', 'Speaker 2', etc., "
    "in order of appearance, unless a speaker introduces themselves by name in the audio, "
    "in which case use their actual name. Give start_time and end_time for every segment in "
    "seconds (floats) relative to the start of this audio chunk. Preserve the original spoken "
    "language and code-switching verbatim; never translate into English. Do not omit spoken content."
)


class TranscriptSegmentDict(TypedDict, total=False):
    speaker: str
    start_time: float
    end_time: float
    text: str
    language_code: str | None


@dataclass
class TranscriptionResult:
    segments: list[TranscriptSegmentDict]
    language_code: str | None = None
    language_confidence: float | None = None
    is_multilingual: bool = False
    language_name: str | None = None


class TranscriptionProvider(ABC):
    supports_multilingual = True
    supports_diarization = False

    @abstractmethod
    def transcribe(self, audio_path: Path, meeting_id: str) -> TranscriptionResult:
        raise NotImplementedError

    def supports_language(self, code: str) -> bool:
        try:
            from faster_whisper.tokenizer import _LANGUAGE_CODES
        except ImportError:
            return False
        return code.casefold() in _LANGUAGE_CODES

    def detect_language(self, result: TranscriptionResult) -> str | None:
        return result.language_code


def _primary_audio_language(scores: dict[str, float], total: float) -> tuple[str | None, float | None, bool]:
    if not scores or total <= 0:
        return None, None, False
    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    code, score = ranked[0]
    share = score / total
    mixed = len(ranked) > 1 and ranked[1][1] / total >= 0.15
    if share < APP_CONFIG.language.minimum_confidence:
        return None, None, mixed
    return code, round(share, 3), mixed


def build_diarization_prompt(known_speakers: list[str]) -> str:
    """Constructs a speaker-continuity prompt passing known speaker labels across sequential chunks."""
    base = "Transcribe original-language speech, including code-switching, with speaker segmentation and timestamps."
    if known_speakers:
        base += (
            " These speakers were already identified earlier in this same meeting — reuse the "
            "same speaker numbers/labels for them if you recognize the same voices: "
            + "; ".join(known_speakers)
        )
    return base


def _transcribe_local_audio(audio_path: Path) -> TranscriptionResult:
    """Run real local Whisper ASR. Unknown speaker identity is labelled conservatively."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Local transcription requires faster-whisper") from exc

    cfg = APP_CONFIG.transcription
    if cfg.model.endswith(".en") and APP_CONFIG.language.multilingual_transcription:
        raise RuntimeError("The configured Whisper checkpoint is English-only; select a multilingual checkpoint")
    language_hint = APP_CONFIG.language.default_language
    language_hint = None if language_hint == "auto" else language_hint
    model = WhisperModel(cfg.model, device=cfg.device, compute_type=cfg.compute_type)
    chunks = split_audio(
        audio_path,
        meeting_id=audio_path.stem,
        chunk_length_ms=cfg.chunk_seconds * 1000,
        overlap_ms=cfg.overlap_seconds * 1000,
    )
    rows: list[dict[str, Any]] = []
    language_scores: dict[str, float] = defaultdict(float)
    total_speech = 0.0
    try:
        for chunk in chunks:
            offset = chunk["start_offset_ms"] / 1000.0
            segments, info = model.transcribe(
                str(chunk["path"]), vad_filter=True, beam_size=5,
                language=language_hint, task="transcribe",
                multilingual=APP_CONFIG.language.multilingual_transcription,
                condition_on_previous_text=False,
            )
            chunk_duration = 0.0
            for segment in segments:
                content = segment.text.strip()
                if content:
                    chunk_duration += max(0.0, float(segment.end) - float(segment.start))
                    rows.append({
                        "speaker": "Speaker 1",
                        "start_time": round(float(segment.start) + offset, 3),
                        "end_time": round(float(segment.end) + offset, 3),
                        "text": content,
                    })
            code = getattr(info, "language", None)
            confidence = float(getattr(info, "language_probability", 0.0) or 0.0)
            total_speech += chunk_duration
            if APP_CONFIG.language.enable_detection and code and confidence >= APP_CONFIG.language.minimum_confidence:
                language_scores[code] += chunk_duration * confidence
    finally:
        cleanup_temp_chunks(chunks)
    code, confidence, mixed = _primary_audio_language(language_scores, total_speech)
    return TranscriptionResult(
        segments=[TranscriptSegmentDict(**row) for row in dedupe_overlap_segments(rows, cfg.overlap_seconds)],
        language_code=code, language_confidence=confidence, is_multilingual=mixed,
    )


def _transcribe_hf_space(audio_path: Path, meeting_id: str) -> TranscriptionResult:
    """Transcribes audio via Hugging Face ZeroGPU Gradio Space (faster-whisper + pyannote diarization).

    Supports direct single-pass audio requests or chunked execution for extra-long recordings.
    """
    if not settings.HF_SPACE_ID:
        raise ValueError("HF_SPACE_ID is not configured.")

    from gradio_client import Client, handle_file

    client = Client(
        settings.HF_SPACE_ID,
        token=settings.HF_API_TOKEN or None,
    )

    chunks = split_audio(audio_path, meeting_id=meeting_id)
    all_segments: list[dict[str, Any]] = []
    language_scores: dict[str, float] = defaultdict(float)
    total_speech = 0.0

    try:
        for idx, chunk in enumerate(chunks):
            chunk_path = chunk["path"]
            offset_seconds = chunk["start_offset_ms"] / 1000.0

            logger.info(
                "[HF_SPACE] Transcribing chunk %d/%d for meeting %s (offset: %.1fs)...",
                idx + 1,
                len(chunks),
                meeting_id,
                offset_seconds,
            )

            result = client.predict(
                audio_file=handle_file(str(chunk_path)),
                min_speakers=None,
                max_speakers=None,
                language=None if APP_CONFIG.language.default_language == "auto" else APP_CONFIG.language.default_language,
                api_name="/transcribe",
            )

            chunk_segments = result.get("segments", []) if isinstance(result, dict) else result
            if not isinstance(chunk_segments, list):
                raise ValueError(f"Unexpected response format from HF Space: {type(result)}")

            for seg in chunk_segments:
                normalized = dict(seg)
                normalized["start_time"] = round(float(seg["start_time"]) + offset_seconds, 3)
                normalized["end_time"] = round(float(seg["end_time"]) + offset_seconds, 3)
                all_segments.append(normalized)
            if isinstance(result, dict) and APP_CONFIG.language.enable_detection:
                code = result.get("language")
                confidence = float(result.get("language_confidence") or 0.0)
                speech = sum(max(0.0, float(s["end_time"]) - float(s["start_time"])) for s in chunk_segments)
                total_speech += speech
                if code and confidence >= APP_CONFIG.language.minimum_confidence:
                    language_scores[code] += speech * confidence

    finally:
        cleanup_temp_chunks(chunks)

    final_segments = dedupe_overlap_segments(all_segments, overlap_seconds=OVERLAP_MS / 1000.0)

    segments = [
        TranscriptSegmentDict(
            speaker=s.get("speaker", "Speaker 1"),
            start_time=float(s.get("start_time", 0.0)),
            end_time=float(s.get("end_time", 0.0)),
            text=s.get("text", ""),
            language_code=s.get("language_code"),
        )
        for s in final_segments
    ]
    code, confidence, mixed = _primary_audio_language(language_scores, total_speech)
    return TranscriptionResult(segments, code, confidence, mixed)


def _transcribe_gemini(audio_path: Path, meeting_id: str) -> TranscriptionResult:
    """Transcribes audio using sequential Gemini audio understanding + diarization."""
    from app.services.gemini_client import generate_json
    chunks = split_audio(audio_path, meeting_id=meeting_id)
    known_speakers: list[str] = []
    all_segments: list[dict[str, Any]] = []

    try:
        for idx, chunk in enumerate(chunks):
            chunk_path = chunk["path"]
            offset_seconds = chunk["start_offset_ms"] / 1000.0
            prompt = build_diarization_prompt(known_speakers)

            logger.info(
                "[GEMINI_AUDIO] Transcribing chunk %d/%d for meeting %s (offset: %.1fs)...",
                idx + 1,
                len(chunks),
                meeting_id,
                offset_seconds,
            )

            result = generate_json(
                prompt=prompt,
                response_schema=_GEMINI_SCHEMA,
                system_instruction=_GEMINI_SYSTEM_INSTRUCTION,
                audio_path=chunk_path,
            )

            chunk_segments = result.get("segments", [])
            for seg in chunk_segments:
                seg["start_time"] = round(float(seg["start_time"]) + offset_seconds, 3)
                seg["end_time"] = round(float(seg["end_time"]) + offset_seconds, 3)
                all_segments.append(seg)

            chunk_speakers = result.get("speaker_descriptions", [])
            if chunk_speakers:
                known_speakers = chunk_speakers
            elif chunk_segments:
                unique_speakers = list({s["speaker"] for s in chunk_segments if s.get("speaker")})
                known_speakers = [f"{spk} (voice from previous segment)" for spk in unique_speakers]

    finally:
        cleanup_temp_chunks(chunks)

    final_segments = dedupe_overlap_segments(all_segments, overlap_seconds=OVERLAP_MS / 1000.0)

    return TranscriptionResult([
        TranscriptSegmentDict(
            speaker=s.get("speaker", "Speaker 1"),
            start_time=float(s.get("start_time", 0.0)),
            end_time=float(s.get("end_time", 0.0)),
            text=s.get("text", ""),
            language_code=s.get("language_code"),
        )
        for s in final_segments
    ])


class LocalWhisperProvider(TranscriptionProvider):
    def transcribe(self, audio_path: Path, meeting_id: str) -> TranscriptionResult:
        return _transcribe_local_audio(audio_path)


class HuggingFaceDiarizationProvider(TranscriptionProvider):
    supports_diarization = True

    def transcribe(self, audio_path: Path, meeting_id: str) -> TranscriptionResult:
        return _transcribe_hf_space(audio_path, meeting_id)


class GeminiTranscriptionProvider(TranscriptionProvider):
    supports_diarization = True

    def transcribe(self, audio_path: Path, meeting_id: str) -> TranscriptionResult:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Gemini transcription selected without GEMINI_API_KEY")
        return _transcribe_gemini(audio_path, meeting_id)


def get_transcription_provider() -> TranscriptionProvider:
    providers = {
        "local": LocalWhisperProvider,
        "huggingface": HuggingFaceDiarizationProvider,
        "gemini": GeminiTranscriptionProvider,
    }
    try:
        return providers[APP_CONFIG.transcription.provider]()
    except KeyError as exc:
        raise RuntimeError(f"Unsupported transcription provider: {APP_CONFIG.transcription.provider}") from exc


def transcribe_audio_with_metadata(audio_path: Path, meeting_id: str | None = None) -> TranscriptionResult:
    """Transcribe original speech, retaining provider and text language evidence."""
    m_id = meeting_id or audio_path.stem
    result = get_transcription_provider().transcribe(audio_path, m_id)
    if isinstance(result, list):  # Compatibility with existing provider adapters.
        result = TranscriptionResult(result)
    if not result.segments:
        raise RuntimeError(f"Transcription produced no speech for meeting {m_id}")
    if APP_CONFIG.language.enable_detection:
        full_text = " ".join(segment["text"] for segment in result.segments)
        text_detection = detect_text_language(full_text)
        if result.language_code is None and text_detection.code:
            result.language_code = text_detection.code
            result.language_confidence = text_detection.confidence
        segment_languages: set[str] = set()
        for segment in result.segments:
            if segment.get("language_code"):
                segment_languages.add(segment["language_code"])
                continue
            detected = detect_text_language(segment["text"])
            segment["language_code"] = detected.code
            if detected.code:
                segment_languages.add(detected.code)
        result.is_multilingual = result.is_multilingual or len(segment_languages) > 1
    result.language_name = language_label(result.language_code)
    return result


def transcribe_audio(audio_path: Path, meeting_id: str | None = None) -> list[TranscriptSegmentDict]:
    """Backward-compatible segment-only entrypoint."""
    return transcribe_audio_with_metadata(audio_path, meeting_id).segments
