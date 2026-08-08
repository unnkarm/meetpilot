import uuid

from sqlalchemy.orm import Session

from app.models.transcript import TranscriptSegment
from app.services.gemini_client import embed_text, generate_text
from app.services.transcript_utils import format_timestamp

_SYSTEM_INSTRUCTION = (
    "You answer questions about a specific meeting using only the transcript excerpts provided. "
    "Be concise and factual. If the excerpts don't contain the answer, say you couldn't find it "
    "in this meeting. When you do answer, mention the relevant timestamp(s) in mm:ss format so "
    "the person can jump to that part of the recording."
)

TOP_K = 6


def _retrieve_relevant_segments(db: Session, meeting_id: uuid.UUID, question: str) -> list[TranscriptSegment]:
    question_embedding = embed_text(question, task_type="RETRIEVAL_QUERY")

    return (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id, TranscriptSegment.embedding.is_not(None))
        .order_by(TranscriptSegment.embedding.cosine_distance(question_embedding))
        .limit(TOP_K)
        .all()
    )


def answer_question(db: Session, meeting_id: uuid.UUID, question: str) -> tuple[str, str | None]:
    """Returns (answer_text, cited_timestamp_or_None)."""
    segments = _retrieve_relevant_segments(db, meeting_id, question)

    if not segments:
        return (
            "I couldn't find any transcribed content for this meeting yet. "
            "It may still be processing.",
            None,
        )

    # Keep excerpts in chronological order for a coherent context window.
    segments = sorted(segments, key=lambda s: s.start_time)
    context = "\n".join(
        f"[{format_timestamp(s.start_time)}] {s.speaker}: {s.text}" for s in segments
    )

    prompt = f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}"
    answer = generate_text(prompt, system_instruction=_SYSTEM_INSTRUCTION)

    cited_timestamp = format_timestamp(segments[0].start_time)
    return answer, cited_timestamp
