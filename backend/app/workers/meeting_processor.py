import logging
import uuid

from app.core.celery_app import celery_app
from app.core.rate_limiter import RateLimitError
from app.database.session import SessionLocal
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingStatus, MeetingSummary
from app.models.notification import Notification, NotificationType
from app.models.task import Task, TaskPriority
from app.models.transcript import TranscriptSegment
from app.services.gemini_client import embed_texts
from app.services.meeting_analysis import generate_meeting_insights
from app.services.storage import resolve_local_path
from app.services.transcript_utils import segments_to_text
from app.services.transcription import transcribe_audio

logger = logging.getLogger(__name__)


@celery_app.task(
    name="process_meeting",
    bind=True,
    autoretry_for=(RateLimitError,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=5,
)
def process_meeting(self, meeting_id: str) -> None:
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, uuid.UUID(meeting_id))
        if meeting is None:
            logger.error("Meeting %s not found, aborting processing", meeting_id)
            return

        meeting.status = MeetingStatus.processing
        db.commit()

        audio_path = resolve_local_path(meeting.audio_url)

        # 1. Transcription + speaker segmentation with Redis rate limiting & chunking
        raw_segments = transcribe_audio(audio_path, meeting_id=str(meeting.id))
        if not raw_segments:

            raise ValueError("Transcription returned no segments")

        # 2. Embed each segment for later semantic search / chat retrieval
        texts = [s["text"] for s in raw_segments]
        embeddings = embed_texts(texts)

        segment_rows: list[TranscriptSegment] = []
        for seg, embedding in zip(raw_segments, embeddings):
            row = TranscriptSegment(
                meeting_id=meeting.id,
                speaker=seg["speaker"],
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"],
                embedding=embedding,
            )
            db.add(row)
            segment_rows.append(row)
        db.flush()

        transcript_text = segments_to_text(segment_rows)
        duration = int(max((s.end_time for s in segment_rows), default=0))
        meeting.duration_seconds = duration

        # 3. Single-Pass Intelligence Extraction (Summary + Tasks + Decisions) to minimize Free Tier tokens
        participant_names = list({s.speaker for s in segment_rows})
        insights = generate_meeting_insights(transcript_text, participant_names)

        db.add(
            MeetingSummary(
                meeting_id=meeting.id,
                overview=insights["overview"],
                key_takeaways=insights["key_takeaways"],
                next_steps=insights["next_steps"],
            )
        )

        for t in insights.get("tasks", []):
            priority = t.get("priority", "medium")
            if priority not in (p.value for p in TaskPriority):
                priority = "medium"
            db.add(
                Task(
                    meeting_id=meeting.id,
                    title=t.get("title", "Untitled task"),
                    assignee_name=t.get("assignee_name"),
                    due_date=t.get("due_date"),
                    priority=TaskPriority(priority),
                    transcript_timestamp=t.get("transcript_timestamp"),
                )
            )

        for d in insights.get("decisions", []):
            db.add(
                Decision(
                    meeting_id=meeting.id,
                    topic=d.get("topic", "Decision"),
                    outcome=d.get("outcome", ""),
                    transcript_timestamp=d.get("transcript_timestamp"),
                )
            )

        meeting.status = MeetingStatus.completed
        meeting.failure_reason = None
        db.add(
            Notification(
                user_id=meeting.created_by,
                type=NotificationType.meeting_processed,
                message=f"'{meeting.title}' has finished processing.",
                meeting_id=meeting.id,
            )
        )
        db.commit()

        # Trigger external integrations (Discord Webhook digest, etc.)
        try:
            from app.services.discord_service import post_meeting_digest_to_discord

            post_meeting_digest_to_discord(db, meeting.id)
        except Exception as integration_exc:
            logger.warning("Failed to post integration digest: %s", integration_exc)

    except RateLimitError as rate_exc:
        db.rollback()
        retries = getattr(self.request, "retries", 0)
        max_retries = getattr(self, "max_retries", 5)
        logger.warning(
            "Rate limit encountered for meeting %s (retry %d/%d). Celery will auto-retry with exponential backoff & jitter.",
            meeting_id,
            retries,
            max_retries,
        )
        # If retries exhausted, persist failed state
        if retries >= max_retries:
            try:
                meeting = db.get(Meeting, uuid.UUID(meeting_id))
                if meeting is not None:
                    meeting.status = MeetingStatus.failed
                    meeting.failure_reason = (
                        "Google Gemini Free Tier rate limit exceeded after maximum automatic retries. Please retry in a few moments."
                    )
                    db.commit()
            except Exception as save_err:
                logger.error("Failed saving final rate limit failure status: %s", save_err)
        # Re-raise so Celery autoretry_for performs exponential backoff with jitter
        raise rate_exc

    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process meeting %s", meeting_id)
        try:
            db.rollback()
            meeting = db.get(Meeting, uuid.UUID(meeting_id))
            if meeting is not None:
                meeting.status = MeetingStatus.failed
                err_msg = str(exc)
                if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
                    err_msg = "Google Gemini API rate limit / quota exceeded (429 Resource Exhausted). Please check your Gemini API plan or retry in a minute."
                meeting.failure_reason = err_msg
                db.add(
                    Notification(
                        user_id=meeting.created_by,
                        type=NotificationType.meeting_failed,
                        message=f"Processing failed for '{meeting.title}': {err_msg[:100]}",
                        meeting_id=meeting.id,
                    )
                )
                db.commit()
        except Exception as save_err:
            logger.error("Failed saving meeting failure status: %s", save_err)
    finally:
        db.close()
