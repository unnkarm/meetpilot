"""Wake-addressed Pilot intent routing using the existing meeting tools."""

import re
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.models.meeting import Meeting
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.knowledge_chat_service import answer_workspace_knowledge
from app.services.pilot_observability import PilotTrace
from app.services.pilot_phase1 import answer_live_context, execute_explicit_task_command
from app.api.deps import get_meeting_for_member
from app.services.access_control import task_visibility
from app.services.pilot_language import native_intent, is_followup, localized_message
from app.services.pilot_commands import native_task_command


def _request_text(query: str) -> str:
    """Recognize spoken polite requests without making inferred tool calls."""
    return re.sub(r"^(?:(?:can|could|would|will)\s+you\s+|please\s+)+", "", query.strip(), flags=re.IGNORECASE)


def _context_followup(query: str) -> bool:
    return is_followup(query) or bool(re.fullmatch(
        r"(?:please )?(?:make it (?:shorter|longer)|(?:tell me |explain )?more|"
        r"tell me more(?: about (?:that|it))?|expand (?:on )?(?:that|it)|"
        r"say (?:that|it) again|(?:explain|expand on|what about|tell me more about) (?:the )?"
        r"(?:first|second|third|fourth|fifth|last|\d+)(?: (?:point|item|part))?)[.!? ]*",
        _request_text(query), re.IGNORECASE,
    ))


def route_intent(query: str) -> str:
    normalized = _request_text(query).casefold()
    native = native_intent(normalized)
    if native:
        return native
    if re.match(r"(?:create|add)\s+(?:a\s+)?task\s+for\s+", normalized):
        return "action_request"
    if re.match(r"^(?:please\s+)?(?:update|delete|mark)\s+(?:the\s+)?task\b", normalized):
        return "clarification"
    if re.search(r"\b(?:my tasks|assigned to me|open tasks|task list)\b", normalized):
        return "task_query"
    # Historical/document requests must retain their workspace retrieval scope.
    if re.search(r"\b(?:last (?:year|week|month|meetings?)|yesterday|previous week|previous meetings?|historical|across meetings)\b", normalized):
        return "historical_meeting_question"
    if re.search(r"\b(?:summary|summarize|recap|key\s*points?|key takeaways?|main (?:points?|topics?)|catch me up|brief me)\b", normalized):
        return "knowledge_question" if re.search(r"\b(?:documents?|files?)\b", normalized) else "summarize"
    if re.search(r"\bwhat (?:did|have) we (?:just )?(?:discuss(?:ed)?|talk(?:ed)? about|cover(?:ed)?)\b", normalized):
        return "meeting_context_question" if "just" in normalized else "summarize"
    broad_decisions = (re.search(r"\bwhat (?:decisions? (?:did|have) we (?:make|made)|did we (?:decide|agree))\b", normalized)
                       and not re.search(r"\b(?:about|regarding|on|why|how)\b", normalized))
    if broad_decisions or re.search(r"\b(?:what (?:have we been discussing|we have discussed)|meeting so far)\b", normalized):
        return "meeting_context_question" if re.search(r"\b(?:just|right now)\b", normalized) else "summarize"
    if re.search(r"\b(?:list (?:the )?decisions|decision list|show (?:me )?(?:the )?decisions)\b", normalized):
        return "decision_query"
    if re.search(r"\b(?:this meeting|the meeting|we (?:just )?(?:discussed|decided|agreed)|our discussion)\b", normalized):
        return "meeting_context_question"
    if re.search(r"\b(?:workspace|documents?|files?|project|knowledge)\b", normalized):
        return "knowledge_question"
    if re.match(r"^(?:hello|hi|hey|thanks|thank you|how are you|are you there|hear me|"
                r"good morning|good afternoon|what can you do)[.!? ]*$", normalized):
        return "general_conversation"
    return "meeting_context_question"


def execute_pilot_query(db: Session, meeting_id: uuid.UUID, workspace_id: uuid.UUID,
                        user: User, query: str, wake_word: str, trace: PilotTrace,
                        *, conversation_history: list[dict] | None = None) -> dict:
    meeting = get_meeting_for_member(meeting_id, user, db)
    if meeting.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Meeting belongs to another workspace")
    with trace.stage("intent_route"):
        intent = route_intent(query)
        followup = _context_followup(query)
        previous_queries = [item.get("content", "") for item in (conversation_history or [])[-6:]
                            if isinstance(item, dict) and item.get("role") == "user"
                            and isinstance(item.get("content"), str)]
        if followup and previous_queries:
            previous_topic = next((text for text in reversed(previous_queries) if not _context_followup(text)), previous_queries[-1])
            previous_intent = route_intent(previous_topic)
            if previous_intent in {"summarize", "knowledge_question", "historical_meeting_question"}:
                intent = previous_intent
    if intent == "action_request":
        try:
            with trace.stage("task_tool"):
                command = re.sub(r"^add\s+", "create ", _request_text(query), flags=re.IGNORECASE).rstrip("?! ")
                # Wake recognition happened before this tool boundary. The
                # command parser's canonical prefix accepts custom wake aliases.
                if native_intent(query) == "action_request":
                    command = native_task_command(db, meeting, user, query)
                    task = execute_explicit_task_command(db, meeting_id, user, command, source_command=query)
                else:
                    task = execute_explicit_task_command(db, meeting_id, user, f"Hey Pilot, {command}")
            return {"intent": intent, "answer": localized_message("created_task", query, "Created task: {task}.").format(task=task.title), "citations": [], "task_id": str(task.id)}
        except HTTPException as exc:
            return {"intent": intent, "answer": localized_message("task_failed", query, f"[Uncertain: {exc.detail}]"), "citations": [], "error_detail": exc.detail}
    if intent == "clarification":
        return {"intent": intent, "answer": localized_message("clarification", query, "Please specify the exact task and change. I have not changed anything."), "citations": []}
    if intent == "general_conversation":
        text = _request_text(query).casefold().strip("।.!? ")
        if text in {"thanks", "thank you", "ধন্যবাদ", "ধন্যবাদ তোমাকে", "धन्यवाद", "शुक्रिया", "dhonnobad", "dhanyavad"}:
            answer = localized_message("thanks", query, "You're welcome.")
        elif text == "what can you do":
            answer = "I can recap this meeting, explain our decisions, find workspace information, and help with your tasks."
        elif text in {"are you there", "hear me"}:
            answer = "Yes, I'm here and listening."
        else:
            answer = localized_message("greeting", query, "Hi, I'm ready. What would you like to know?")
        return {"intent": intent, "answer": answer, "citations": []}
    if intent == "task_query":
        personal = bool(re.search(r"\b(?:my tasks|assigned to me)\b|আমার|আমাকে|मेरे|मुझे|\b(?:amar|mere)\b", query.casefold()))
        with trace.stage("task_tool"):
            task_query = (db.query(Task).join(Meeting, Meeting.id == Task.meeting_id)
                          .filter(Meeting.workspace_id == workspace_id, task_visibility(user.id)))
            if personal:
                task_query = task_query.filter(Task.assignee_id == user.id)
            if re.search(r"\bopen tasks\b", query.casefold()):
                task_query = task_query.filter(Task.status != TaskStatus.done)
            rows = task_query.order_by(Task.created_at.desc()).limit(5).all()
        if not rows:
            return {"intent": intent, "answer": localized_message("no_tasks", query, "I found no matching tasks in this workspace."), "citations": []}
        prefix = localized_message("your_tasks" if personal else "recent_tasks", query, "Your recent tasks: " if personal else "Recent tasks: ")
        return {"intent": intent, "answer": prefix + "; ".join(task.title for task in rows),
                "citations": [{"type": "task", "meeting_id": str(task.meeting_id), "task_id": str(task.id)} for task in rows]}
    if intent == "decision_query":
        with trace.stage("decision_tool"):
            rows = (db.query(Decision).join(Meeting, Meeting.id == Decision.meeting_id)
                    .filter(Meeting.workspace_id == workspace_id, Decision.meeting_id == meeting_id)
                    .order_by(Decision.created_at.desc()).limit(5).all())
        if not rows:
            with trace.stage("meeting_retrieval_qwen"):
                result = answer_live_context(db, meeting_id, user, query, summarize=True,
                                             conversation_history=conversation_history)
            return {"intent": intent, **result}
        return {"intent": intent, "answer": "Recent decisions: " + "; ".join(item.outcome for item in rows),
                "citations": [{"type": "decision", "meeting_id": str(item.meeting_id), "decision_id": str(item.id),
                               "speaker": item.source_speaker, "timestamp": item.transcript_timestamp,
                               "snippet": item.source_quote or item.outcome} for item in rows]}
    if intent in {"knowledge_question", "historical_meeting_question"}:
        with trace.stage("workspace_retrieval_qwen"):
            answer, citations = answer_workspace_knowledge(db, workspace_id, query, user_id=user.id,
                                                           conversation_history=conversation_history)
        return {"intent": intent, "answer": answer, "citations": citations}
    with trace.stage("meeting_retrieval_qwen"):
        result = answer_live_context(db, meeting_id, user, query, summarize=intent == "summarize",
                                     conversation_history=conversation_history)
    return {"intent": intent, **result}
