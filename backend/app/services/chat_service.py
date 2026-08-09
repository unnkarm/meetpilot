import logging
import re
import uuid

from sqlalchemy.orm import Session

from app.models.transcript import TranscriptSegment
from app.services.gemini_client import embed_text, generate_text
from app.services.transcript_utils import format_timestamp

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are MeetPilot AI Assistant. You answer questions about a specific meeting using only the transcript excerpts provided. "
    "Be concise, factual, and strictly grounded in the excerpts. If the excerpts do NOT contain the answer, explicitly state that "
    "you could not find information about that in this meeting. When you do find the answer, cite the exact timestamp(s) in mm:ss format "
    "so the user can verify the spoken turn."
)

TOP_K = 6

_NEGATIVE_PHRASES = [
    "couldn't find",
    "could not find",
    "not mentioned",
    "not discussed",
    "no information",
    "does not mention",
    "doesn't mention",
    "does not contain",
    "no record",
    "not specified",
    "unable to find",
]


def _retrieve_relevant_segments(db: Session, meeting_id: uuid.UUID, question: str) -> list[TranscriptSegment]:
    """Retrieves top-K transcript segments using pgvector cosine distance similarity."""
    question_embedding = embed_text(question, task_type="RETRIEVAL_QUERY")

    return (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id, TranscriptSegment.embedding.is_not(None))
        .order_by(TranscriptSegment.embedding.cosine_distance(question_embedding))
        .limit(TOP_K)
        .all()
    )


def _extract_citation(answer: str, top_segment: TranscriptSegment) -> str | None:
    """Extracts timestamp citation from answer or top semantic match, suppressing on negative answers."""
    answer_lower = answer.lower()
    for neg in _NEGATIVE_PHRASES:
        if neg in answer_lower:
            return None

    # Check for explicit mm:ss timestamp mentioned in the answer
    ts_match = re.search(r"\b(\d{1,2}:\d{2})\b", answer)
    if ts_match:
        return ts_match.group(1)

    # Fallback to the top cosine-similarity segment
    if top_segment and top_segment.start_time is not None:
        return format_timestamp(top_segment.start_time)
    return None


def answer_question(db: Session, meeting_id: uuid.UUID, question: str) -> tuple[str, str | None]:
    """Retrieves relevant transcript chunks using pgvector, prompts Gemini, and extracts verified citations.

    Returns (answer_text, cited_timestamp_or_None).
    """
    try:
        segments = _retrieve_relevant_segments(db, meeting_id, question)
    except Exception as exc:
        logger.error("Error during vector retrieval for meeting %s: %s", meeting_id, exc)
        # Fallback to chronological segments if vector search encounters issue
        segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.meeting_id == meeting_id)
            .order_by(TranscriptSegment.start_time.asc())
            .limit(TOP_K)
            .all()
        )

    if not segments:
        return (
            "I couldn't find any transcribed content for this meeting yet. "
            "The audio may still be processing.",
            None,
        )

    # The first segment in the cosine query result is the most semantically relevant
    top_segment = segments[0]

    # Order excerpts chronologically to construct coherent context window
    sorted_segments = sorted(segments, key=lambda s: s.start_time)
    context = "\n".join(
        f"[{format_timestamp(s.start_time)}] {s.speaker}: {s.text}" for s in sorted_segments
    )

    prompt = f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}"

    try:
        answer = generate_text(prompt, system_instruction=_SYSTEM_INSTRUCTION)
        if not answer.strip():
            answer = "I couldn't find enough information in this meeting transcript to answer that question."
    except Exception as exc:
        logger.error("LLM text generation failed: %s", exc)
        answer = "I encountered an issue querying the intelligence model. Please try asking again in a few moments."
        return answer, None

    cited_timestamp = _extract_citation(answer, top_segment)
    return answer, cited_timestamp
