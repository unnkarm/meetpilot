import logging
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_user_workspace_ids
from app.database.session import get_db
from app.models.decision import Decision
from app.models.document import KnowledgeDocument, DocumentChunk
from app.models.meeting import Meeting
from app.models.task import Task
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.services.gemini_client import embed_text
from app.services.transcript_utils import format_timestamp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])

MAX_VECTOR_RESULTS = 10
MAX_KEYWORD_RESULTS = 10


class SearchResult(BaseModel):
    type: str  # "transcript" | "meeting" | "document" | "task" | "decision"
    meeting_id: Optional[uuid.UUID] = None
    meeting_title: Optional[str] = None
    document_id: Optional[uuid.UUID] = None
    document_title: Optional[str] = None
    page_number: Optional[int] = None
    snippet: str
    speaker: Optional[str] = None
    timestamp: Optional[str] = None
    created_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    query: str
    filter_type: str = "all"
    total_results: int = 0
    results: List[SearchResult]


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    workspace_id: Optional[uuid.UUID] = None,
    filter_type: str = "all",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Executes workspace-scoped hybrid semantic vector + keyword search across meetings, transcripts, documents, tasks, and decisions."""
    user_ws_ids = get_user_workspace_ids(current_user, db)
    raw_filter = getattr(filter_type, "default", filter_type)
    selected_filter = str(raw_filter or "all").lower()

    if workspace_id:
        if workspace_id not in user_ws_ids:
            return SearchResponse(query=q, filter_type=selected_filter, total_results=0, results=[])
        workspace_ids = [workspace_id]
    else:
        workspace_ids = user_ws_ids

    if not workspace_ids:
        return SearchResponse(query=q, filter_type=selected_filter, total_results=0, results=[])

    query_str = q.strip()
    like_pattern = f"%{query_str}%"
    results: List[SearchResult] = []
    seen_keys: set[str] = set()

    # Generate query vector embedding for semantic search
    query_embedding = None
    try:
        query_embedding = embed_text(query_str, task_type="RETRIEVAL_QUERY")
    except Exception as exc:
        logger.warning("Query embedding failed: %s", exc)

    # 1. Search Meeting Transcripts (if filter is 'all' or 'meetings' or 'transcripts')
    if selected_filter in ("all", "meetings", "transcripts"):
        # Vector search on transcript segments
        if query_embedding:
            try:
                vector_matches = (
                    db.query(TranscriptSegment, Meeting.title, Meeting.created_at)
                    .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
                    .filter(
                        Meeting.workspace_id.in_(workspace_ids),
                        TranscriptSegment.embedding.is_not(None),
                    )
                    .order_by(TranscriptSegment.embedding.cosine_distance(query_embedding).asc())
                    .limit(MAX_VECTOR_RESULTS)
                    .all()
                )
                for seg, meeting_title, m_created_at in vector_matches:
                    key = f"transcript-{seg.id}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(
                            SearchResult(
                                type="transcript",
                                meeting_id=seg.meeting_id,
                                meeting_title=meeting_title,
                                snippet=f"[{seg.speaker}] {seg.text}",
                                speaker=seg.speaker,
                                timestamp=format_timestamp(seg.start_time),
                                created_at=m_created_at,
                            )
                        )
            except Exception as exc:
                logger.warning("Vector search on transcripts failed: %s", exc)

        # Keyword search on transcripts
        kw_transcripts = (
            db.query(TranscriptSegment, Meeting.title, Meeting.created_at)
            .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
            .filter(Meeting.workspace_id.in_(workspace_ids), TranscriptSegment.text.ilike(like_pattern))
            .limit(MAX_KEYWORD_RESULTS)
            .all()
        )
        for seg, meeting_title, m_created_at in kw_transcripts:
            key = f"transcript-{seg.id}"
            if key not in seen_keys:
                seen_keys.add(key)
                results.append(
                    SearchResult(
                        type="transcript",
                        meeting_id=seg.meeting_id,
                        meeting_title=meeting_title,
                        snippet=f"[{seg.speaker}] {seg.text}",
                        speaker=seg.speaker,
                        timestamp=format_timestamp(seg.start_time),
                        created_at=m_created_at,
                    )
                )

        # Search Meeting Titles
        meetings = (
            db.query(Meeting)
            .filter(Meeting.workspace_id.in_(workspace_ids), Meeting.title.ilike(like_pattern))
            .limit(MAX_KEYWORD_RESULTS)
            .all()
        )
        for m in meetings:
            key = f"meeting-{m.id}"
            if key not in seen_keys:
                seen_keys.add(key)
                results.append(
                    SearchResult(
                        type="meeting",
                        meeting_id=m.id,
                        meeting_title=m.title,
                        snippet=f"Meeting: {m.title} ({m.status.value})",
                        speaker=None,
                        timestamp=None,
                        created_at=m.created_at,
                    )
                )

    # 2. Search Uploaded Knowledge Documents (if filter is 'all' or 'documents')
    if selected_filter in ("all", "documents"):
        # Vector search on document chunks
        if query_embedding:
            try:
                doc_matches = (
                    db.query(DocumentChunk, KnowledgeDocument.title, KnowledgeDocument.created_at)
                    .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
                    .filter(
                        DocumentChunk.workspace_id.in_(workspace_ids),
                        DocumentChunk.embedding.is_not(None),
                    )
                    .order_by(DocumentChunk.embedding.cosine_distance(query_embedding).asc())
                    .limit(MAX_VECTOR_RESULTS)
                    .all()
                )
                for chunk, doc_title, doc_created_at in doc_matches:
                    key = f"docchunk-{chunk.id}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        page_str = f"Page {chunk.page_number} • " if chunk.page_number else ""
                        results.append(
                            SearchResult(
                                type="document",
                                document_id=chunk.document_id,
                                document_title=doc_title,
                                page_number=chunk.page_number,
                                snippet=f"{page_str}{chunk.text}",
                                created_at=doc_created_at,
                            )
                        )
            except Exception as exc:
                logger.warning("Vector search on document chunks failed: %s", exc)

        # Keyword search on document chunks
        kw_doc_chunks = (
            db.query(DocumentChunk, KnowledgeDocument.title, KnowledgeDocument.created_at)
            .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
            .filter(DocumentChunk.workspace_id.in_(workspace_ids), DocumentChunk.text.ilike(like_pattern))
            .limit(MAX_KEYWORD_RESULTS)
            .all()
        )
        for chunk, doc_title, doc_created_at in kw_doc_chunks:
            key = f"docchunk-{chunk.id}"
            if key not in seen_keys:
                seen_keys.add(key)
                page_str = f"Page {chunk.page_number} • " if chunk.page_number else ""
                results.append(
                    SearchResult(
                        type="document",
                        document_id=chunk.document_id,
                        document_title=doc_title,
                        page_number=chunk.page_number,
                        snippet=f"{page_str}{chunk.text}",
                        created_at=doc_created_at,
                    )
                )

        # Search Document Titles
        docs = (
            db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.workspace_id.in_(workspace_ids), KnowledgeDocument.title.ilike(like_pattern))
            .limit(MAX_KEYWORD_RESULTS)
            .all()
        )
        for d in docs:
            key = f"doc-{d.id}"
            if key not in seen_keys:
                seen_keys.add(key)
                results.append(
                    SearchResult(
                        type="document",
                        document_id=d.id,
                        document_title=d.title,
                        snippet=f"Knowledge Document: {d.title} ({d.file_type.upper()} • {d.chunk_count} chunks)",
                        created_at=d.created_at,
                    )
                )

    # 3. Search Action Items / Tasks (if filter is 'all' or 'tasks')
    if selected_filter in ("all", "tasks"):
        task_rows = (
            db.query(Task, Meeting.title, Meeting.created_at)
            .join(Meeting, Meeting.id == Task.meeting_id)
            .filter(Meeting.workspace_id.in_(workspace_ids), Task.title.ilike(like_pattern))
            .limit(MAX_KEYWORD_RESULTS)
            .all()
        )
        for task, meeting_title, m_created_at in task_rows:
            key = f"task-{task.id}"
            if key not in seen_keys:
                seen_keys.add(key)
                results.append(
                    SearchResult(
                        type="task",
                        meeting_id=task.meeting_id,
                        meeting_title=meeting_title,
                        snippet=f"Task: {task.title} (Assignee: {task.assignee_name or 'Unassigned'}, Priority: {task.priority.value.upper()})",
                        speaker=task.assignee_name,
                        timestamp=task.transcript_timestamp,
                        created_at=m_created_at,
                    )
                )

    # 4. Search Consensus Decisions (if filter is 'all' or 'decisions')
    if selected_filter in ("all", "decisions"):
        decision_rows = (
            db.query(Decision, Meeting.title, Meeting.created_at)
            .join(Meeting, Meeting.id == Decision.meeting_id)
            .filter(
                Meeting.workspace_id.in_(workspace_ids),
                (Decision.topic.ilike(like_pattern)) | (Decision.outcome.ilike(like_pattern)),
            )
            .limit(MAX_KEYWORD_RESULTS)
            .all()
        )
        for decision, meeting_title, m_created_at in decision_rows:
            key = f"decision-{decision.id}"
            if key not in seen_keys:
                seen_keys.add(key)
                results.append(
                    SearchResult(
                        type="decision",
                        meeting_id=decision.meeting_id,
                        meeting_title=meeting_title,
                        snippet=f"Decision: {decision.topic} — {decision.outcome}",
                        speaker=None,
                        timestamp=decision.transcript_timestamp,
                        created_at=m_created_at,
                    )
                )

    return SearchResponse(
        query=q,
        filter_type=selected_filter,
        total_results=len(results),
        results=results,
    )
