"""Wake-addressed Pilot intent routing using the existing meeting tools."""

import re
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.models.meeting import Meeting
from app.models.task import Task
from app.models.user import User
from app.services.knowledge_chat_service import answer_workspace_knowledge
from app.services.pilot_observability import PilotTrace
from app.services.pilot_phase1 import answer_live_context, execute_explicit_task_command
from app.api.deps import get_meeting_for_member


def route_intent(query: str) -> str:
    normalized = query.strip().casefold()
    if re.match(r"^(?:please\s+)?create\s+(?:a\s+)?task\s+for\s+", normalized):
        return "action_request"
    if re.match(r"^(?:please\s+)?(?:update|delete|mark)\s+(?:the\s+)?task\b", normalized):
        return "clarification"
    if re.search(r"\b(?:my tasks|assigned to me|open tasks|task list)\b", normalized):
        return "task_query"
    if re.search(r"\b(?:decisions|decided|decision list)\b", normalized) and not re.search(r"\b(?:just|now|today)\b", normalized):
        return "decision_query"
    if re.match(r"^(?:summarize|summary|recap)\b", normalized):
        return "summarize"
    if re.search(r"\b(?:last year|last week|previous week|previous meetings?|historical|across meetings)\b", normalized):
        return "historical_meeting_question"
    if re.search(r"\b(?:workspace|documents?|files?|project|knowledge)\b", normalized):
        return "knowledge_question"
    if re.match(r"^(?:hello|hi|thanks|thank you)[.!? ]*$", normalized):
        return "general_conversation"
    return "meeting_context_question"


def execute_pilot_query(db: Session, meeting_id: uuid.UUID, workspace_id: uuid.UUID,
                        user: User, query: str, wake_word: str, trace: PilotTrace) -> dict:
    meeting = get_meeting_for_member(meeting_id, user, db)
    if meeting.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Meeting belongs to another workspace")
    with trace.stage("intent_route"):
        intent = route_intent(query)
    if intent == "action_request":
        try:
            with trace.stage("task_tool"):
                task = execute_explicit_task_command(db, meeting_id, user, f"{wake_word}, {query}")
            return {"intent": intent, "answer": f"Created task: {task.title}.", "citations": [], "task_id": str(task.id)}
        except HTTPException as exc:
            return {"intent": intent, "answer": f"[Uncertain: {exc.detail}]", "citations": []}
    if intent == "clarification":
        return {"intent": intent, "answer": "Please specify the exact task and change. I have not changed anything.", "citations": []}
    if intent == "general_conversation":
        return {"intent": intent, "answer": "How can I help with this meeting?", "citations": []}
    if intent == "task_query":
        with trace.stage("task_tool"):
            rows = (db.query(Task).join(Meeting, Meeting.id == Task.meeting_id)
                    .filter(Meeting.workspace_id == workspace_id, Task.assignee_id == user.id)
                    .order_by(Task.created_at.desc()).limit(5).all())
        if not rows:
            return {"intent": intent, "answer": "I found no tasks assigned to you in this workspace.", "citations": []}
        return {"intent": intent, "answer": "Your recent tasks: " + "; ".join(task.title for task in rows),
                "citations": [{"type": "task", "meeting_id": str(task.meeting_id), "task_id": str(task.id)} for task in rows]}
    if intent == "decision_query":
        with trace.stage("decision_tool"):
            rows = (db.query(Decision).join(Meeting, Meeting.id == Decision.meeting_id)
                    .filter(Meeting.workspace_id == workspace_id, Decision.meeting_id == meeting_id)
                    .order_by(Decision.created_at.desc()).limit(5).all())
        if not rows:
            return {"intent": intent, "answer": "I found no recorded decisions for this meeting.", "citations": []}
        return {"intent": intent, "answer": "Recent decisions: " + "; ".join(item.outcome for item in rows),
                "citations": [{"type": "decision", "meeting_id": str(item.meeting_id), "decision_id": str(item.id)} for item in rows]}
    if intent in {"knowledge_question", "historical_meeting_question"}:
        with trace.stage("workspace_retrieval_qwen"):
            answer, citations = answer_workspace_knowledge(db, workspace_id, query, user_id=user.id)
        return {"intent": intent, "answer": answer, "citations": citations}
    with trace.stage("meeting_retrieval_qwen"):
        result = answer_live_context(db, meeting_id, user, query)
    return {"intent": intent, **result}
