import logging
import os
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

CHUNK_LENGTH_MS = 15 * 60 * 1000  # 15 min chunks (tune to quota)
OVERLAP_MS = 15 * 1000  # 15s overlap for boundary context


class ChunkInfo(TypedDict):
    path: Path
    start_offset_ms: int
    duration_ms: int
    is_temp: bool


def split_audio(
    file_path: Path,
    meeting_id: str,
    chunk_length_ms: int = CHUNK_LENGTH_MS,
    overlap_ms: int = OVERLAP_MS,
) -> list[ChunkInfo]:
    """Splits long audio (>15m) into sequential overlapping chunks.

    Returns a list of ChunkInfo dicts with local start_offset_ms to re-align
    timestamps back to the full meeting timeline.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found at: {file_path}")

    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(str(file_path))
        total_len = len(audio)

        # If audio is within single chunk limit, return as single chunk without slicing
        if total_len <= chunk_length_ms:
            return [
                {
                    "path": file_path,
                    "start_offset_ms": 0,
                    "duration_ms": total_len,
                    "is_temp": False,
                }
            ]

        logger.info(
            "Audio duration is %.1f mins (>15m limit). Splitting into overlapping chunks for meeting %s...",
            total_len / 60000.0,
            meeting_id,
        )

        tmp_dir = Path("/tmp") if os.path.exists("/tmp") else file_path.parent
        chunks: list[ChunkInfo] = []
        start = 0
        chunk_idx = 0

        while start < total_len:
            end = min(start + chunk_length_ms, total_len)
            chunk_audio = audio[start:end]
            chunk_file = tmp_dir / f"{meeting_id}_chunk_{chunk_idx}.wav"

            # Export sliced WAV chunk
            chunk_audio.export(str(chunk_file), format="wav")
            chunks.append(
                {
                    "path": chunk_file,
                    "start_offset_ms": start,
                    "duration_ms": end - start,
                    "is_temp": True,
                }
            )

            if end == total_len:
                break

            # Step forward by chunk length minus overlap
            start = end - overlap_ms
            chunk_idx += 1

        return chunks

    except Exception as exc:
        logger.warning(
            "pydub audio chunking unavailable or audio format unsupported (%s). Falling back to direct audio processing.",
            exc,
        )
        return [
            {
                "path": file_path,
                "start_offset_ms": 0,
                "duration_ms": 0,
                "is_temp": False,
            }
        ]


def dedupe_overlap_segments(segments: list[dict[str, Any]], overlap_seconds: float = 15.0) -> list[dict[str, Any]]:
    """Deduplicates the overlap seam region across consecutive chunks.

    Drops segments from chunk N+1 that start before chunk N's segments ended,
    preserving chunk N's segments which have more preceding acoustic context.
    """
    if not segments:
        return []

    # Ensure chronological order
    sorted_segments = sorted(segments, key=lambda s: s.get("start_time", 0.0))
    deduped: list[dict[str, Any]] = []

    for seg in sorted_segments:
        if deduped:
            prev_end = deduped[-1].get("end_time", 0.0)
            # If this segment begins significantly before the previous segment ended within the overlap window, skip it
            if seg.get("start_time", 0.0) < (prev_end - (overlap_seconds / 2.0)):
                continue

        deduped.append(seg)

    return deduped


def cleanup_temp_chunks(chunks: list[ChunkInfo]) -> None:
    """Removes temporary sliced chunk files from disk after transcription."""
    for ch in chunks:
        if ch.get("is_temp", False) and ch["path"].exists():
            try:
                ch["path"].unlink()
            except Exception as exc:
                logger.warning("Failed removing temporary chunk file %s: %s", ch["path"], exc)
