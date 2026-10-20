"""Bound summary evidence across a meeting's complete recorded timeline."""

from sqlalchemy import func

from app.models.transcript import TranscriptSegment
from app.models.decision import Decision
from app.models.pilot_memory import PilotMemory
from app.models.task import Task
from app.models.meeting import Meeting
from app.services.access_control import task_visibility
from app.core.app_config import APP_CONFIG
from app.services.knowledge_retriever import Evidence
from app.services.transcript_utils import format_timestamp


def _clip_quote(text: str, limit: int) -> str:
    content = " ".join(text.split())
    if len(content) <= limit:
        return content
    if limit < 4:
        return content[:limit]
    prefix = content[:limit - 1]
    if " " in prefix:
        prefix = prefix.rsplit(" ", 1)[0]
    return prefix.rstrip() + "…"


def _highlight_ids(db, meeting, user_id, limit: int = 12) -> list:
    """Keep source-linked agreements/commitments even between timeline samples.

    We use the original transcript turn, not generated summary/task prose.
    Structured tasks remain subject to the requester's task visibility.
    """
    if limit <= 0:
        return []
    decisions = (db.query(Decision.source_segment_id).join(
        TranscriptSegment, TranscriptSegment.id == Decision.source_segment_id,
    ).filter(
        Decision.meeting_id == meeting.id, Decision.source_segment_id.is_not(None),
        TranscriptSegment.meeting_id == meeting.id,
    ).order_by(Decision.created_at.desc()).limit(6).all())
    memories = (db.query(PilotMemory.source_segment_id).join(
        TranscriptSegment, TranscriptSegment.id == PilotMemory.source_segment_id,
    ).filter(
        PilotMemory.meeting_id == meeting.id, PilotMemory.workspace_id == meeting.workspace_id,
        TranscriptSegment.meeting_id == meeting.id,
        PilotMemory.confidence >= APP_CONFIG.pilot.memory_confidence_threshold,
    ).order_by(PilotMemory.created_at.desc()).limit(6).all())
    tasks = []
    if user_id is not None:
        tasks = (db.query(Task.source_segment_id).join(Meeting, Meeting.id == Task.meeting_id).join(
            TranscriptSegment, TranscriptSegment.id == Task.source_segment_id,
        ).filter(
            Task.meeting_id == meeting.id, task_visibility(user_id), Task.source_segment_id.is_not(None),
            TranscriptSegment.meeting_id == meeting.id,
        ).order_by(Task.created_at.desc()).limit(6).all())
    # Interleave categories rather than consuming every slot with one kind.
    ids = []
    for index in range(6):
        for rows in (decisions, memories, tasks):
            if len(rows) > index and rows[index][0] not in ids:
                ids.append(rows[index][0])
                if len(ids) >= limit:
                    return ids
    return ids


def summary_timeline_evidence(db, meeting, max_chars: int, max_segments: int = 64,
                              *, user_id=None) -> tuple[list[Evidence], dict]:
    """Select uniformly across time order instead of only the last live turns.

    The SQL window samples bounded rows even for long meetings. Evidence text is
    budgeted equally so the context limit cannot silently discard the end. When
    sampling or clipping is needed, the returned coverage explicitly says so.
    Callers must authorize the meeting before using this helper.
    """
    total = db.query(func.count(TranscriptSegment.id)).filter(TranscriptSegment.meeting_id == meeting.id).scalar() or 0
    if not total:
        return [], {"kind": "meeting_timeline", "total_segments": 0, "included_segments": 0, "complete": True}
    count = min(total, max_segments, max(1, max_chars // 160))
    ordered = (TranscriptSegment.start_time, TranscriptSegment.id)
    if total <= count:
        segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting.id).order_by(*ordered).limit(count).all()
    else:
        highlights = _highlight_ids(db, meeting, user_id, limit=min(12, max(0, count - 2)))
        timeline_count = max(2, count - len(highlights)) if count > 1 else 1
        positions = ([1 + round(index * (total - 1) / (timeline_count - 1)) for index in range(timeline_count)]
                     if timeline_count > 1 else [total])
        ranked = db.query(
            TranscriptSegment.id.label("segment_id"),
            func.row_number().over(order_by=ordered).label("position"),
        ).filter(TranscriptSegment.meeting_id == meeting.id).subquery()
        segments = (db.query(TranscriptSegment).join(ranked, ranked.c.segment_id == TranscriptSegment.id)
                    .filter(ranked.c.position.in_(positions) | TranscriptSegment.id.in_(highlights))
                    .order_by(*ordered).all())
    if not segments:
        return [], {"kind": "meeting_timeline", "total_segments": total, "included_segments": 0, "complete": False}
    # Reserve enough space per line for [S64] and a newline, share the initial
    # budget fairly, then give unused space from short turns to longer ones.
    # An uneven but small transcript should never be clipped unnecessarily.
    prefixes = [f"{format_timestamp(segment.start_time)} {segment.speaker[:60]}: " for segment in segments]
    contents = [" ".join(segment.text.split()) for segment in segments]
    per_line = max(1, max_chars // len(segments) - 8)
    allowances = [min(len(content), max(1, per_line - len(prefix))) for content, prefix in zip(contents, prefixes)]
    spare = max(0, max_chars - sum(len(prefix) + allowance + 8 for prefix, allowance in zip(prefixes, allowances)))
    while spare > 0:
        pending = [index for index, content in enumerate(contents) if len(content) > allowances[index]]
        if not pending:
            break
        portion = max(1, spare // len(pending))
        for index in pending:
            increase = min(spare, portion, len(contents[index]) - allowances[index])
            allowances[index] += increase
            spare -= increase
            if not spare:
                break
    evidence = []
    clipped = False
    for index, segment in enumerate(segments):
        timestamp = format_timestamp(segment.start_time)
        prefix = prefixes[index]
        quote = _clip_quote(segment.text, allowances[index])
        clipped = clipped or len(quote) < len(contents[index])
        key = f"transcript:{segment.id}"
        evidence.append(Evidence(
            key, prefix + quote,
            {"type": "meeting", "meeting_id": str(meeting.id), "title": meeting.title,
             "speaker": segment.speaker, "timestamp": timestamp, "snippet": segment.text[:200]},
        ))
    return evidence, {
        "kind": "meeting_timeline", "total_segments": total, "included_segments": len(evidence),
        "complete": len(evidence) == total and not clipped,
        "first_timestamp": format_timestamp(segments[0].start_time),
        "last_timestamp": format_timestamp(segments[-1].start_time),
    }
