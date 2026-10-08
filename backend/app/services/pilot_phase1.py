"""Bounded live context and conservative, source-backed Pilot memory.

This service consumes final transcript turns stored by the live meeting bot.
It never calls the LLM for each turn and does not infer identity from speaker numbers.
"""

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_meeting_for_member
from app.core.app_config import APP_CONFIG
from app.services.ai_provider import get_ai_provider
from app.services.knowledge_chat_service import GroundedAnswer, INSUFFICIENT, indexed_evidence
from app.services.knowledge_retriever import KnowledgeRetriever, Evidence
from app.services.language_detection import detect_text_language, language_label
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingParticipant
from app.models.pilot_memory import PilotMemory, PilotMemoryKind
from app.models.task import Task, TaskPriority
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.transcript_utils import format_timestamp
from app.services.pilot_observability import PilotTrace
from app.services.access_control import require_manager, task_visibility

logger = logging.getLogger(__name__)


def _require_pilot_enabled() -> None:
    if not APP_CONFIG.pilot.enabled:
        raise HTTPException(status_code=503, detail="Pilot is disabled")


@dataclass(frozen=True)
class MemoryCandidate:
    kind: str
    text: str
    confidence: float
    assignee_name: str | None = None
    due_date: str | None = None


def classify_live_statement(text: str) -> MemoryCandidate | None:
    """Store only explicit signals; ambiguous conversation stays in the transcript."""
    content = " ".join(text.strip().split())
    if len(content) < 12 or content.endswith("?"):
        return None
    lower = content.casefold()
    if re.search(r"\b(could|might|maybe|perhaps|should|consider|propose|possibly)\b", lower):
        return None
    if re.search(r"\b(we decided to|we have decided to|we agreed to|okay,? let's|let's go with)\b", lower):
        return MemoryCandidate("decision", content, 0.96)
    task = re.match(r"(?P<name>[\w'-]{2,60}),\s*please\s+(?P<action>.{5,})", content, re.IGNORECASE | re.UNICODE)
    if task:
        due_match = re.search(r"\b(?:by|due)\s+(\d{4}-\d{2}-\d{2})\b", content, re.IGNORECASE)
        due_date = None
        if due_match:
            try:
                due_date = date.fromisoformat(due_match.group(1)).isoformat()
            except ValueError:
                pass
        return MemoryCandidate("task", task.group("action").rstrip(".!"), 0.94, task.group("name"), due_date)
    if re.match(r"(?:I will|I'll|I commit to)\s+.{5,}", content, re.IGNORECASE):
        return MemoryCandidate("commitment", content, 0.90)
    if re.match(r"(?:The deadline is|Deadline:)\s+\d{4}-\d{2}-\d{2}\b", content, re.IGNORECASE):
        return MemoryCandidate("deadline", content, 0.97)
    if re.match(r"(?:Fact|Confirmed fact):\s+.{8,}", content, re.IGNORECASE):
        return MemoryCandidate("fact", content, 0.88)
    if re.match(r"(?:For the record|Important context):?\s+.{8,}", content, re.IGNORECASE):
        return MemoryCandidate("important_context", content, 0.88)
    return None


def _verified_participant(db: Session, meeting: Meeting, name: str) -> User | None:
    """Only an explicitly linked meeting participant can become an assignee."""
    participants = (
        db.query(MeetingParticipant)
        .filter(MeetingParticipant.meeting_id == meeting.id, func.lower(MeetingParticipant.name) == name.casefold())
        .all()
    )
    ids = {person.user_id for person in participants if person.user_id}
    if not participants or any(person.user_id is None for person in participants) or len(ids) != 1:
        return None
    if any(not (person.identity_verified_by or
                (person.email_verified and (person.identity_confidence or 0) >= APP_CONFIG.pilot.identity_confidence_threshold))
           and person.user_id != meeting.created_by for person in participants):
        return None
    if any(person.provider and (person.identity_confidence or 0) < APP_CONFIG.pilot.identity_confidence_threshold
           for person in participants):
        return None
    if APP_CONFIG.pilot.identity_confidence_threshold > 1.0:
        return None
    user_id = next(iter(ids))
    if db.get(WorkspaceMember, (meeting.workspace_id, user_id)) is None:
        return None
    return db.get(User, user_id)


def process_live_segment(db: Session, meeting: Meeting, segment: TranscriptSegment) -> str | None:
    """Persist high-confidence items once; caller handles failures without stopping capture."""
    if not APP_CONFIG.pilot.enabled or not APP_CONFIG.pilot.memory_enabled or meeting.status.value != "in_progress":
        return None
    trace = PilotTrace(meeting.id, meeting.workspace_id)
    with trace.stage("passive_classification"):
        candidate = classify_live_statement(segment.text)
    if candidate is None or candidate.confidence < APP_CONFIG.pilot.memory_confidence_threshold:
        return None
    with trace.stage("passive_persistence"):
        return _persist_live_candidate(db, meeting, segment, candidate)


def safely_process_live_segment(db: Session, meeting: Meeting, segment: TranscriptSegment) -> str | None:
    """Keep Pilot failures from interrupting the meeting transcript consumer."""
    try:
        return process_live_segment(db, meeting, segment)
    except Exception:
        db.rollback()
        logger.exception("Pilot passive extraction failed meeting=%s workspace=%s", meeting.id, meeting.workspace_id)
        return None


def _persist_live_candidate(db: Session, meeting: Meeting, segment: TranscriptSegment, candidate: MemoryCandidate) -> str | None:
    if candidate.kind == "task":
        if db.query(Task).filter(
            Task.meeting_id == meeting.id,
            func.lower(Task.title) == candidate.text.casefold(),
        ).first():
            return None
        assignee = _verified_participant(db, meeting, candidate.assignee_name or "")
        task = Task(
            meeting_id=meeting.id, title=candidate.text,
            assignee_id=assignee.id if assignee else None,
            assignee_name=assignee.name if assignee else candidate.assignee_name,
            due_date=candidate.due_date,
            priority=TaskPriority.medium,
            source_segment_id=segment.id,
            source_speaker=segment.speaker,
            source_quote=segment.text,
            transcript_timestamp=format_timestamp(segment.start_time),
            extraction_confidence=candidate.confidence,
            prompt_version="pilot-passive-rules-v1",
        )
        db.add(task)
    elif candidate.kind == "decision":
        if db.query(Decision).filter(
            Decision.meeting_id == meeting.id,
            func.lower(Decision.outcome) == candidate.text.casefold(),
        ).first():
            return None
        db.add(Decision(
            meeting_id=meeting.id, topic=candidate.text[:500], outcome=candidate.text,
            source_segment_id=segment.id, source_speaker=segment.speaker,
            source_quote=segment.text,
            transcript_timestamp=format_timestamp(segment.start_time),
            extraction_confidence=candidate.confidence,
            prompt_version="pilot-passive-rules-v1",
        ))
    else:
        kind = PilotMemoryKind(candidate.kind)
        existing = db.query(PilotMemory).filter(
            PilotMemory.meeting_id == meeting.id,
            PilotMemory.kind == kind,
            func.lower(PilotMemory.text) == candidate.text.casefold(),
        ).first()
        if existing:
            return None
        db.add(PilotMemory(
            id=uuid.uuid4(), meeting_id=meeting.id, workspace_id=meeting.workspace_id,
            source_segment_id=segment.id, kind=kind, text=candidate.text,
            source_speaker=segment.speaker, confidence=candidate.confidence,
            language_code=segment.language_code,
        ))
    db.commit()
    return candidate.kind


def build_live_context(db: Session, meeting_id: uuid.UUID, user: User, trace: PilotTrace | None = None) -> dict:
    meeting = get_meeting_for_member(meeting_id, user, db)
    _require_pilot_enabled()
    trace = trace or PilotTrace(meeting.id, meeting.workspace_id)
    with trace.stage("context_load"):
        count = APP_CONFIG.pilot.context_window
        segments = list(reversed(db.query(TranscriptSegment).filter(
            TranscriptSegment.meeting_id == meeting.id,
        ).order_by(TranscriptSegment.start_time.desc()).limit(count).all()))
        tasks = db.query(Task).join(Meeting, Meeting.id == Task.meeting_id).filter(Task.meeting_id == meeting.id, task_visibility(user.id)).order_by(Task.created_at.desc()).limit(5).all()
        decisions = db.query(Decision).filter(Decision.meeting_id == meeting.id).order_by(Decision.created_at.desc()).limit(5).all()
        memories = db.query(PilotMemory).filter(PilotMemory.meeting_id == meeting.id, PilotMemory.workspace_id == meeting.workspace_id).order_by(PilotMemory.created_at.desc()).limit(APP_CONFIG.pilot.memory_limit).all()
    return {
        "meeting_id": str(meeting.id), "workspace_id": str(meeting.workspace_id),
        "meeting_title": meeting.title, "language_code": meeting.language_code,
        "current_user_id": str(user.id),
        "active_speakers": list(dict.fromkeys(s.speaker for s in reversed(segments)))[:5],
        "recent_segments": [
            {"id": str(s.id), "speaker": s.speaker, "text": s.text,
             "start_time": s.start_time, "end_time": s.end_time, "language_code": s.language_code}
            for s in segments
        ],
        "recent_topics": [d.topic for d in decisions[:3]],
        "recent_decisions": [
            {"id": str(d.id), "text": d.outcome, "speaker": d.source_speaker,
             "source_segment_id": str(d.source_segment_id) if d.source_segment_id else None}
            for d in decisions
        ],
        "recent_tasks": [
            {"id": str(t.id), "title": t.title, "speaker": t.source_speaker,
             "assignee_name": t.assignee_name, "source_segment_id": str(t.source_segment_id) if t.source_segment_id else None}
            for t in tasks
        ],
        "recent_memory": [
            {"kind": m.kind.value, "text": m.text, "speaker": m.source_speaker,
             "source_segment_id": str(m.source_segment_id)} for m in memories
        ],
    }


def answer_live_context(db: Session, meeting_id: uuid.UUID, user: User, question: str) -> dict:
    """Ground Qwen in recent live turns plus the existing meeting-scoped retriever."""
    meeting = get_meeting_for_member(meeting_id, user, db)
    _require_pilot_enabled()
    if not question.strip():
        raise HTTPException(status_code=422, detail="Question is required")
    trace = PilotTrace(meeting.id, meeting.workspace_id)
    with trace.stage("total_response"):
        return _answer_live_context(db, meeting, user, question, trace)


def _answer_live_context(db: Session, meeting: Meeting, user: User, question: str, trace: PilotTrace) -> dict:
    context = build_live_context(db, meeting.id, user, trace=trace)
    evidence: dict[str, Evidence] = {}
    for item in context["recent_segments"]:
        evidence_id = "transcript:" + item["id"]
        evidence[evidence_id] = Evidence(
            evidence_id, f"{item['speaker']}: {item['text']}",
            {"type": "meeting", "meeting_id": str(meeting.id), "title": meeting.title,
             "speaker": item["speaker"], "timestamp": format_timestamp(item["start_time"]),
             "snippet": item["text"][:200]},
        )
    try:
        with trace.stage("retrieval"):
            for item in KnowledgeRetriever(db, meeting.workspace_id).retrieve(question, meeting_id=meeting.id):
                evidence.setdefault(item.id, item)
    except Exception:
        logger.exception("Pilot retrieval failed meeting=%s workspace=%s", meeting.id, meeting.workspace_id)
    if not evidence:
        trace.event("answer_result", "insufficient", 0.0)
        return {"answer": INSUFFICIENT, "citations": []}
    selected_evidence = list(evidence.values())[:APP_CONFIG.rag.top_k * 4]
    source_text, available = indexed_evidence(selected_evidence, APP_CONFIG.rag.max_context_chars)
    if not source_text:
        return {"answer": INSUFFICIENT, "citations": []}
    detected = detect_text_language(question)
    answer_language = language_label(detected.code)
    instruction = f"Answer in {answer_language}." if answer_language else "Answer in the question's language when clear."
    try:
        with trace.stage("qwen_reasoning"):
            result = get_ai_provider().structured(
                f"{instruction} Answer concisely using only the cited meeting evidence. "
                "The latest speech is included even if it is not embedded yet. "
                "Preserve names and technical terms. Return the short S1, S2 source labels used. "
                "If the evidence is insufficient, return no source IDs. "
                f"Meeting: {meeting.title}.\nEvidence:\n{source_text}\nQuestion: {question}",
                GroundedAnswer,
            )
    except Exception:
        logger.exception("Pilot context answer failed meeting=%s workspace=%s", meeting.id, meeting.workspace_id)
        trace.event("answer_result", "model_unavailable", 0.0)
        return {"answer": "[Uncertain: The local model could not produce a reliable answer. Please try again.]", "citations": []}
    citations = [available[source_id].citation for source_id in result.source_ids if source_id in available]
    if not citations:
        trace.event("answer_result", "insufficient", 0.0)
        return {"answer": INSUFFICIENT, "citations": []}
    trace.event("answer_result", "answered", 0.0)
    return {"answer": result.answer.strip(), "citations": citations}


_TASK_COMMAND = re.compile(
    r"^hey\s+pilot,?\s+(?:please\s+)?create\s+(?:a\s+)?task\s+for\s+"
    r"(?P<assignee>[\w .'-]{2,80}?)\s+to\s+(?P<action>[^?]{5,400})[.!]?$",
    re.IGNORECASE | re.UNICODE,
)


_WEEKDAYS = {name: index for index, name in enumerate(
    ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
)}


def _task_action_and_deadline(action: str) -> tuple[str, str | None]:
    content = action.strip().rstrip(".!")
    match = re.search(r"\s+by\s+(\d{4}-\d{2}-\d{2}|monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
                      content, re.IGNORECASE)
    if not match:
        return content, None
    deadline = match.group(1).lower()
    if deadline in _WEEKDAYS:
        today = date.today()
        deadline = (today + timedelta(days=(_WEEKDAYS[deadline] - today.weekday()) % 7)).isoformat()
    else:
        try:
            deadline = date.fromisoformat(deadline).isoformat()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Task deadline must be a valid date") from exc
    return content[:match.start()].strip(), deadline


def execute_explicit_task_command(db: Session, meeting_id: uuid.UUID, user: User, command: str) -> Task:
    """Only a direct, wake-addressed user command can create a task."""
    meeting = get_meeting_for_member(meeting_id, user, db)
    require_manager(db, meeting.workspace_id, user.id)
    _require_pilot_enabled()
    trace = PilotTrace(meeting.id, meeting.workspace_id)
    with trace.stage("action_total"):
        return _execute_explicit_task_command(db, meeting, user, command, trace)


def _execute_explicit_task_command(db: Session, meeting: Meeting, user: User, command: str, trace: PilotTrace) -> Task:
    match = _TASK_COMMAND.fullmatch(command.strip())
    if not match:
        raise HTTPException(status_code=422, detail="Use an explicit 'Hey Pilot, create a task for NAME to ACTION' command")
    assignee_name = match.group("assignee").strip()
    with trace.stage("identity_resolution"):
        members = db.query(User).join(WorkspaceMember, WorkspaceMember.user_id == User.id).filter(
            WorkspaceMember.workspace_id == meeting.workspace_id,
            func.lower(User.name) == assignee_name.casefold(),
        ).all()
    if len(members) != 1:
        raise HTTPException(status_code=422, detail="Assignee must uniquely match a workspace member")
    try:
        with trace.stage("task_tool"):
            title, due_date = _task_action_and_deadline(match.group("action"))
            task = Task(
                meeting_id=meeting.id, title=title, assignee_id=members[0].id,
                assignee_name=members[0].name, due_date=due_date,
                priority=TaskPriority.medium, source_speaker=getattr(user, "name", None),
                source_quote=command.strip(), extraction_confidence=1.0,
                prompt_version="pilot-explicit-command-v1",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Pilot task action failed meeting=%s workspace=%s", meeting.id, meeting.workspace_id)
        raise HTTPException(status_code=503, detail="Task action is temporarily unavailable") from exc
