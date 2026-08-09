import logging
import re
import uuid
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.document import KnowledgeDocument, DocumentChunk
from app.models.meeting import Meeting
from app.models.transcript import TranscriptSegment
from app.services.gemini_client import embed_text, generate_text

logger = logging.getLogger(__name__)

MAX_DOCUMENT_CHUNKS = 5
MAX_TRANSCRIPT_SEGMENTS = 5


def _format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def answer_workspace_knowledge(
    db: Session,
    workspace_id: uuid.UUID,
    question: str,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Answers a workspace-wide question using grounded RAG from both Workspace Documents and Meeting Transcripts."""
    query_str = question.strip()
    if not query_str:
        return "Please provide a question to search your workspace knowledge base.", []

    retrieved_citations: List[Dict[str, Any]] = []
    context_blocks: List[str] = []

    # 1. Embed query vector
    query_embedding = embed_text(query_str, task_type="RETRIEVAL_QUERY")

    # 2. Retrieve relevant Document Chunks from pgvector
    matched_doc_chunks: List[Tuple[DocumentChunk, str]] = []
    if query_embedding:
        try:
            doc_rows = (
                db.query(DocumentChunk, KnowledgeDocument.title)
                .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
                .filter(
                    DocumentChunk.workspace_id == workspace_id,
                    DocumentChunk.embedding.is_not(None),
                )
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding).asc())
                .limit(MAX_DOCUMENT_CHUNKS)
                .all()
            )
            matched_doc_chunks = doc_rows
        except Exception as exc:
            logger.warning(f"Vector search on document chunks failed: {exc}")

    # Fallback/supplemental keyword search on documents if vector yielded few results
    if len(matched_doc_chunks) < 3:
        try:
            kw_doc_rows = (
                db.query(DocumentChunk, KnowledgeDocument.title)
                .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
                .filter(
                    DocumentChunk.workspace_id == workspace_id,
                    DocumentChunk.text.ilike(f"%{query_str}%"),
                )
                .limit(3)
                .all()
            )
            existing_chunk_ids = {c[0].id for c in matched_doc_chunks}
            for row in kw_doc_rows:
                if row[0].id not in existing_chunk_ids:
                    matched_doc_chunks.append(row)
        except Exception as exc:
            logger.warning(f"Keyword search on document chunks failed: {exc}")

    # Format document context
    for chunk, doc_title in matched_doc_chunks:
        page_info = f", Page {chunk.page_number}" if chunk.page_number else ""
        context_blocks.append(
            f'[DOCUMENT: "{doc_title}"{page_info}]\n{chunk.text.strip()}'
        )
        retrieved_citations.append({
            "type": "document",
            "title": doc_title,
            "document_id": str(chunk.document_id),
            "page_number": chunk.page_number,
            "snippet": chunk.text[:200] + ("..." if len(chunk.text) > 200 else ""),
        })

    # 3. Retrieve relevant Meeting Transcripts from pgvector
    matched_transcript_segs: List[Tuple[TranscriptSegment, str, uuid.UUID]] = []
    if query_embedding:
        try:
            seg_rows = (
                db.query(TranscriptSegment, Meeting.title, Meeting.id)
                .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
                .filter(
                    Meeting.workspace_id == workspace_id,
                    TranscriptSegment.embedding.is_not(None),
                )
                .order_by(TranscriptSegment.embedding.cosine_distance(query_embedding).asc())
                .limit(MAX_TRANSCRIPT_SEGMENTS)
                .all()
            )
            matched_transcript_segs = seg_rows
        except Exception as exc:
            logger.warning(f"Vector search on meeting transcripts failed: {exc}")

    # Format meeting transcript context
    for seg, meeting_title, meeting_id in matched_transcript_segs:
        ts_str = _format_timestamp(seg.start_time)
        context_blocks.append(
            f'[MEETING TRANSCRIPT: "{meeting_title}" @ {ts_str} | {seg.speaker}]\n{seg.text.strip()}'
        )
        retrieved_citations.append({
            "type": "meeting",
            "title": meeting_title,
            "meeting_id": str(meeting_id),
            "timestamp": ts_str,
            "speaker": seg.speaker,
            "snippet": seg.text[:200] + ("..." if len(seg.text) > 200 else ""),
        })

    # If no relevant context in workspace
    if not context_blocks:
        return (
            "I couldn't find any relevant company documents or meeting transcripts in your workspace matching this query. "
            "Upload company documents (PDF, DOCX, TXT, MD) or record meetings to populate your workspace knowledge base.",
            [],
        )

    # 4. Construct Grounded RAG Prompt
    system_instruction = (
        "You are the MeetPilot Workspace AI Knowledge Assistant. "
        "You answer questions using company documentation and meeting transcripts. "
        "Strict rules:\n"
        "1. Base your answer strictly on the provided Context blocks.\n"
        "2. If comparing meeting discussions with company documents, clearly contrast both sources.\n"
        "3. Explicitly cite the document names (and page numbers if available) and meeting titles (and timestamps).\n"
        "4. If the context does not contain sufficient information to answer the question, state that clearly without guessing."
    )

    combined_context = "\n\n---\n\n".join(context_blocks)
    prompt = f"""Context from Workspace Knowledge Base:
{combined_context}

Question:
{query_str}

Grounded Answer:"""

    try:
        answer = generate_text(prompt, system_instruction=system_instruction, temperature=0.2)
        answer = answer.strip()
    except Exception as exc:
        logger.error(f"Gemini generation error in knowledge chat: {exc}")
        answer = (
            "I retrieved relevant sources from your workspace, but encountered an error generating the final summary. "
            "Please review the cited sources below or try again in a moment."
        )

    # Filter citations to only include sources that are relevant / referenced
    negative_phrases = [
        "couldn't find",
        "could not find",
        "does not contain",
        "no information",
        "not mentioned",
        "no documents or transcripts",
    ]
    if any(phrase in answer.lower() for phrase in negative_phrases) and len(answer) < 200:
        return answer, []

    return answer, retrieved_citations
