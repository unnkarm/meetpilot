"""Meeting-scoped Ask MeetPilot using the shared workspace retriever."""

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.app_config import APP_CONFIG
from app.models.meeting import Meeting
from app.services.ai_provider import get_ai_provider
from app.services.knowledge_chat_service import GroundedAnswer, INSUFFICIENT
from app.services.knowledge_retriever import KnowledgeRetriever
from app.services.language_detection import detect_text_language, language_label

logger = logging.getLogger(__name__)


def answer_question(db: Session, meeting_id: uuid.UUID, question: str) -> tuple[str, str | None]:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        return "Meeting not found.", None
    evidence = KnowledgeRetriever(db, meeting.workspace_id).retrieve(question, meeting_id=meeting_id)
    if not evidence:
        return "I couldn't find enough evidence in this meeting to answer that question.", None
    context = "\n\n".join(f"[{item.id}] {item.text}" for item in evidence)[: APP_CONFIG.rag.max_context_chars]
    question_language = detect_text_language(question)
    answer_language = language_label(question_language.code)
    language_instruction = (
        f"Answer in {answer_language}, the language of the question."
        if APP_CONFIG.language.qa_language_mode == "question" and answer_language else
        "Answer in the language of the question when clear."
    )
    try:
        result = get_ai_provider().structured(
            f"Prompt version: {APP_CONFIG.language.prompt_version}. "
            f"{language_instruction} Understand evidence in its original language, including code-switching. "
            "Preserve names, APIs, product names and technical terms. "
            "Answer using only the meeting transcript evidence. Return IDs of sources used. "
            "If the evidence is insufficient, say so and return empty source_ids.\n\n"
            f"Evidence:\n{context}\n\nQuestion: {question}",
            GroundedAnswer,
        )
    except Exception:
        logger.exception("Meeting answer generation failed meeting=%s", meeting_id)
        return "The AI model could not produce a reliable answer. Please try again.", None
    by_id = {item.id: item for item in evidence if f"[{item.id}]" in context}
    selected = [by_id[source_id] for source_id in result.source_ids if source_id in by_id]
    if not selected:
        return INSUFFICIENT, None
    return result.answer.strip(), selected[0].citation.get("timestamp")
