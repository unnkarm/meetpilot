"""Workspace answers with validated citations to retrieved evidence IDs."""

import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.app_config import APP_CONFIG
from app.services.ai_provider import get_ai_provider
from app.services.knowledge_retriever import KnowledgeRetriever
from app.services.language_detection import detect_text_language, language_label

logger = logging.getLogger(__name__)
INSUFFICIENT = "[Uncertain: I couldn't find enough evidence in this workspace to answer that question.]"


class GroundedAnswer(BaseModel):
    answer: str = Field(min_length=1)
    source_ids: list[str]


def indexed_evidence(items, max_chars: int) -> tuple[str, dict]:
    """Give the local model short citation handles while retaining source IDs."""
    lines = []
    available = {}
    used = 0
    for index, item in enumerate(items, start=1):
        alias = f"S{index}"
        line = f"[{alias}] {item.text}"
        if used + len(line) + (1 if lines else 0) > max_chars:
            break
        lines.append(line)
        used += len(line) + (1 if lines else 0)
        available[alias] = item
        available[item.id] = item  # Also accept existing callers/tests using full IDs.
    return "\n".join(lines), available


def answer_workspace_knowledge(db: Session, workspace_id: uuid.UUID, question: str) -> tuple[str, list[dict[str, Any]]]:
    if not question.strip():
        return "Please enter a question.", []

    evidence = KnowledgeRetriever(db, workspace_id).retrieve(question)
    if not evidence:
        return INSUFFICIENT, []

    context, by_id = indexed_evidence(evidence, APP_CONFIG.rag.max_context_chars)
    if not context:
        return INSUFFICIENT, []
    question_language = detect_text_language(question)
    answer_language = language_label(question_language.code)
    language_instruction = (
        f"Answer in {answer_language}, the language of the question."
        if APP_CONFIG.language.qa_language_mode == "question" and answer_language else
        "Answer in the language of the question when clear."
    )
    prompt = (
        f"Prompt version: {APP_CONFIG.language.prompt_version}. {language_instruction} "
        "Read multilingual and code-switched evidence in its original language. "
        "Preserve proper nouns, names, URLs and technical terms. "
        "Answer using only the evidence below. Return the short S1, S2 source labels used. "
        "If the evidence does not answer the question, say so and return an empty source_ids array. "
        "Do not invent facts or cite IDs absent from the evidence.\n\n"
        f"Evidence:\n{context}\n\nQuestion: {question}"
    )
    try:
        result = get_ai_provider().structured(prompt, GroundedAnswer)
    except Exception:
        logger.exception("Workspace answer generation failed workspace=%s", workspace_id)
        return "[Uncertain: The local model could not produce a reliable answer. Please try again.]", []

    selected = [by_id[source_id] for source_id in result.source_ids if source_id in by_id]
    if not selected:
        return INSUFFICIENT, []
    return result.answer.strip(), [item.citation for item in selected]
