"""Workspace-scoped retrieval for Ask MeetPilot and meeting chat."""

import logging
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.app_config import APP_CONFIG
from app.models.decision import Decision
from app.models.document import DocumentChunk, KnowledgeDocument
from app.models.meeting import Meeting
from app.models.pilot_memory import PilotMemory
from app.models.task import Task
from app.models.transcript import TranscriptSegment
from app.services.embedding_provider import embed_text
from app.services.transcript_utils import format_timestamp

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Evidence:
    id: str
    text: str
    citation: dict


class KnowledgeRetriever:
    def __init__(self, db: Session, workspace_id: uuid.UUID):
        self.db = db
        self.workspace_id = workspace_id

    def retrieve(self, question: str, meeting_id: uuid.UUID | None = None) -> list[Evidence]:
        top_k = APP_CONFIG.rag.top_k
        matches: dict[str, Evidence] = {}
        vector = None
        try:
            vector = embed_text(question, task_type="RETRIEVAL_QUERY")
        except Exception:
            logger.exception("Query embedding failed workspace=%s", self.workspace_id)

        if vector is not None:
            try:
                distance = DocumentChunk.embedding.cosine_distance(vector)
                if meeting_id is None:
                    rows = (
                        self.db.query(DocumentChunk, KnowledgeDocument.title)
                        .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
                        .filter(DocumentChunk.workspace_id == self.workspace_id,
                                KnowledgeDocument.workspace_id == self.workspace_id,
                                DocumentChunk.embedding.is_not(None),
                                DocumentChunk.embedding_model == APP_CONFIG.embeddings.model,
                                distance <= APP_CONFIG.rag.similarity_threshold)
                        .order_by(distance).limit(top_k).all()
                    )
                    for chunk, title in rows:
                        self._add_document(matches, chunk, title)
            except Exception:
                logger.exception("Document vector retrieval failed workspace=%s", self.workspace_id)

            try:
                distance = TranscriptSegment.embedding.cosine_distance(vector)
                query = (
                    self.db.query(TranscriptSegment, Meeting.title)
                    .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
                    .filter(Meeting.workspace_id == self.workspace_id,
                            TranscriptSegment.embedding.is_not(None),
                            TranscriptSegment.embedding_model == APP_CONFIG.embeddings.model,
                            distance <= APP_CONFIG.rag.similarity_threshold)
                )
                if meeting_id:
                    query = query.filter(Meeting.id == meeting_id)
                for segment, title in query.order_by(distance).limit(top_k).all():
                    self._add_transcript(matches, segment, title)
            except Exception:
                logger.exception("Transcript vector retrieval failed workspace=%s", self.workspace_id)

        words = [word for word in re.findall(r"[^\W_]{2,}", question.casefold(), flags=re.UNICODE)
                 if word not in {"what", "which", "when", "where", "about", "from", "with", "were", "have", "show", "last"}]
        words = list(dict.fromkeys(words))[:5]
        if words:
            if meeting_id is None:
                rows = (
                    self.db.query(DocumentChunk, KnowledgeDocument.title)
                    .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
                    .filter(DocumentChunk.workspace_id == self.workspace_id,
                            KnowledgeDocument.workspace_id == self.workspace_id,
                            or_(*(DocumentChunk.text.ilike(f"%{word}%") for word in words)))
                    .limit(top_k).all()
                )
                for chunk, title in rows:
                    self._add_document(matches, chunk, title)

            query = (
                self.db.query(TranscriptSegment, Meeting.title)
                .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
                .filter(Meeting.workspace_id == self.workspace_id,
                        or_(*(TranscriptSegment.text.ilike(f"%{word}%") for word in words)))
            )
            if meeting_id:
                query = query.filter(Meeting.id == meeting_id)
            for segment, title in query.limit(top_k).all():
                self._add_transcript(matches, segment, title)

            if meeting_id is None:
                task_rows = (
                    self.db.query(Task, Meeting.title)
                    .join(Meeting, Meeting.id == Task.meeting_id)
                    .filter(Meeting.workspace_id == self.workspace_id,
                            or_(*(Task.title.ilike(f"%{word}%") for word in words)))
                    .limit(top_k).all()
                )
                for task, title in task_rows:
                    key = f"task:{task.id}"
                    matches[key] = Evidence(key, f"Task: {task.title}. Assignee: {task.assignee_name or 'Unassigned'}. Status: {task.status.value}.",
                                            {"type": "task", "title": title, "meeting_id": str(task.meeting_id),
                                             "timestamp": task.transcript_timestamp, "snippet": task.title})
                decision_rows = (
                    self.db.query(Decision, Meeting.title)
                    .join(Meeting, Meeting.id == Decision.meeting_id)
                    .filter(Meeting.workspace_id == self.workspace_id,
                            or_(*((Decision.topic.ilike(f"%{word}%")) | (Decision.outcome.ilike(f"%{word}%")) for word in words)))
                    .limit(top_k).all()
                )
                for decision, title in decision_rows:
                    key = f"decision:{decision.id}"
                    matches[key] = Evidence(key, f"Decision: {decision.topic}. Outcome: {decision.outcome}.",
                                            {"type": "decision", "title": title, "meeting_id": str(decision.meeting_id),
                                             "timestamp": decision.transcript_timestamp, "snippet": decision.outcome})
            memory_query = (
                self.db.query(PilotMemory, Meeting.title, TranscriptSegment.start_time)
                .join(Meeting, Meeting.id == PilotMemory.meeting_id)
                .join(TranscriptSegment, TranscriptSegment.id == PilotMemory.source_segment_id)
                .filter(PilotMemory.workspace_id == self.workspace_id,
                        Meeting.workspace_id == self.workspace_id,
                        or_(*(PilotMemory.text.ilike(f"%{word}%") for word in words)))
            )
            if meeting_id:
                memory_query = memory_query.filter(PilotMemory.meeting_id == meeting_id)
            for memory, title, start_time in memory_query.limit(top_k).all():
                key = f"memory:{memory.id}"
                matches[key] = Evidence(
                    key, memory.text,
                    {"type": "meeting", "title": title, "meeting_id": str(memory.meeting_id),
                     "timestamp": format_timestamp(start_time), "speaker": memory.source_speaker,
                     "snippet": memory.text[:200]},
                )
        return list(matches.values())[: top_k * 4]

    @staticmethod
    def _add_document(matches: dict[str, Evidence], chunk: DocumentChunk, title: str) -> None:
        key = f"document:{chunk.id}"
        matches[key] = Evidence(key, chunk.text,
                                {"type": "document", "title": title, "document_id": str(chunk.document_id),
                                 "page_number": chunk.page_number, "snippet": chunk.text[:200]})

    @staticmethod
    def _add_transcript(matches: dict[str, Evidence], segment: TranscriptSegment, title: str) -> None:
        key = f"transcript:{segment.id}"
        matches[key] = Evidence(key, f"{segment.speaker}: {segment.text}",
                                {"type": "meeting", "title": title, "meeting_id": str(segment.meeting_id),
                                 "timestamp": format_timestamp(segment.start_time), "speaker": segment.speaker,
                                 "snippet": segment.text[:200]})
