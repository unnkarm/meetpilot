from app.models.transcript import TranscriptSegment


def format_timestamp(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def segments_to_text(segments: list[TranscriptSegment]) -> str:
    lines = []
    for seg in segments:
        lines.append(f"[{format_timestamp(seg.start_time)}] {seg.speaker}: {seg.text}")
    return "\n".join(lines)
