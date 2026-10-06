import logging
import re
import uuid
from datetime import datetime, timezone

from app.core.app_config import APP_CONFIG
from app.core.celery_app import celery_app
from app.core.rate_limiter import RateLimitError
from app.database.session import SessionLocal
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus, MeetingSummary
from app.models.notification import Notification, NotificationType
from app.models.task import Task, TaskPriority
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.embedding_provider import embed_texts
from app.services.meeting_analysis import (
    DECISION_EXTRACTION_PROMPT_VERSION,
    SUMMARY_PROMPT_VERSION,
    TASK_EXTRACTION_PROMPT_VERSION,
    generate_meeting_insights,
)
from app.services.language_detection import detect_text_language, language_label
from app.services.storage import resolve_local_path
from app.services.transcript_utils import format_timestamp, segments_to_text
from app.services.transcription import TranscriptionResult, transcribe_audio_with_metadata
from app.services.product_events import track_event

logger = logging.getLogger(__name__)


def _source_segment(value: str | None, segments: list[TranscriptSegment]) -> TranscriptSegment | None:
    """Accept evidence only when the model points inside persisted speech."""
    try:
        parts = [int(part) for part in (value or "").split(":")]
        seconds = parts[0] * 60 + parts[1] if len(parts) == 2 else None
    except ValueError:
        return None
    if seconds is None:
        return None
    for segment in segments:
        if segment.start_time - 2 <= seconds <= segment.end_time + 2:
            return segment
    return None


def _supported_by_source(claim: str, source: TranscriptSegment, source_quote: str | None = None) -> bool:
    """Reject a cited action/topic with no substantive overlap with its speech turn."""
    if source_quote:
        quote = " ".join(source_quote.casefold().split())
        speech = " ".join(source.text.casefold().split())
        speaker_prefix = source.speaker.casefold() + ":"
        if quote.startswith(speaker_prefix):
            quote = quote[len(speaker_prefix):].strip()
        return len(quote) >= 8 and quote in speech
    excluded = {"will", "with", "that", "this", "from", "have", "make", "next",
                "please", "about", "team", "meeting", "action", "agreed", "decision"}
    terms = set(re.findall(r"[^\W_]{3,}", claim.casefold(), flags=re.UNICODE)) - excluded
    spoken = set(re.findall(r"[^\W_]{3,}", source.text.casefold(), flags=re.UNICODE))
    return bool(terms & spoken)


def _grounded_section(items: list[dict], segments: list[TranscriptSegment]) -> list[dict]:
    result = []
    for item in items:
        source = _source_segment(item.get("transcript_timestamp"), segments)
        quote = item.get("source_quote")
        if source is None or not quote or not _supported_by_source(item.get("text", ""), source, quote):
            continue
        result.append({"text": item["text"], "speaker": source.speaker,
                       "timestamp": format_timestamp(source.start_time), "source_quote": quote,
                       "source_segment_id": str(source.id)})
    return result


def _claim(db, meeting_id: uuid.UUID) -> Meeting | None:
    """Atomically claim a queued job; duplicate Celery deliveries exit."""
    changed = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.status == MeetingStatus.queued)
        .update({Meeting.status: MeetingStatus.transcribing,
                 Meeting.processing_updated_at: datetime.now(timezone.utc)}, synchronize_session=False)
    )
    db.commit()
    return db.get(Meeting, meeting_id) if changed else None


def process_transcript_intelligence(
    db, meeting: Meeting, raw_segments: list[dict], transcription: TranscriptionResult | None = None,
) -> None:
    """Shared downstream intelligence pipeline: embeddings, summary, tasks, decisions, and notifications."""
    for segment in raw_segments:
        if not segment.get("language_code"):
            segment["language_code"] = detect_text_language(segment["text"]).code
    existing_segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting.id)
        .order_by(TranscriptSegment.start_time)
        .all()
    )

    same_source = len(existing_segments) == len(raw_segments) and all(
        old.text == new["text"] and abs(old.start_time - new["start_time"]) < 0.01
        for old, new in zip(existing_segments, raw_segments)
    )
    if same_source:
        segment_rows = existing_segments
        for row, segment in zip(segment_rows, raw_segments):
            if segment.get("language_code"):
                row.language_code = segment["language_code"]
    else:
        db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting.id).delete()
        db.flush()
        segment_rows = []
        for seg in raw_segments:
            row = TranscriptSegment(
                meeting_id=meeting.id,
                speaker=seg["speaker"],
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"],
                language_code=seg.get("language_code"),
            )
            db.add(row)
            segment_rows.append(row)
        db.flush()

    # Source text survives a later embedding or LLM failure.
    detected = detect_text_language(" ".join(row.text for row in segment_rows))
    meeting.language_code = (transcription.language_code if transcription else None) or detected.code
    meeting.language_name = language_label(meeting.language_code)
    meeting.language_confidence = (
        transcription.language_confidence if transcription and transcription.language_code else detected.confidence
    )
    meeting.is_multilingual = bool(
        (transcription and transcription.is_multilingual)
        or len({row.language_code for row in segment_rows if row.language_code}) > 1
    )
    db.commit()
    meeting.status = MeetingStatus.embedding
    meeting.processing_updated_at = datetime.now(timezone.utc)
    db.commit()
    embeddings = embed_texts([row.text for row in segment_rows])
    for row, embedding in zip(segment_rows, embeddings):
        row.embedding = embedding
        row.embedding_model = APP_CONFIG.embeddings.model
    db.commit()
    transcript_text = segments_to_text(segment_rows)
    duration = int(max((s.end_time for s in segment_rows), default=0))
    meeting.duration_seconds = max(meeting.duration_seconds or 0, duration)

    # Single-Pass Intelligence Extraction (Summary + Tasks + Decisions) to minimize tokens
    participant_names = list({s.speaker for s in segment_rows if s.speaker})

    # Synchronize identified speaker labels into meeting participants.
    existing_participant_names = {p.name for p in meeting.participants}
    for name in participant_names:
        if name and name not in existing_participant_names:
            db.add(
                MeetingParticipant(
                    meeting_id=meeting.id,
                    name=name,
                    role="Participant",
                )
            )
    db.flush()

    meeting.status = MeetingStatus.analyzing
    meeting.processing_updated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Analyzing meeting=%s workspace=%s provider=%s model=%s", meeting.id, meeting.workspace_id,
                APP_CONFIG.ai.provider, APP_CONFIG.ai.model)
    insights = generate_meeting_insights(
        transcript_text, participant_names,
        language_code=meeting.language_code, language_name=meeting.language_name,
        meeting_date=meeting.created_at.date() if meeting.created_at else None,
    )
    members = (
        db.query(User)
        .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .filter(WorkspaceMember.workspace_id == meeting.workspace_id)
        .all()
    )
    members_by_name = {}
    for user in members:
        if user.name:
            members_by_name.setdefault(user.name.casefold(), []).append(user)

    # Clean up any existing summaries, tasks, or decisions for this meeting to ensure idempotent processing
    db.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting.id).delete()
    db.query(Task).filter(Task.meeting_id == meeting.id).delete()
    db.query(Decision).filter(Decision.meeting_id == meeting.id).delete()
    db.flush()

    summary_row = MeetingSummary(
            meeting_id=meeting.id,
            overview=insights["overview"],
            key_takeaways=insights["key_takeaways"],
            next_steps=insights["next_steps"],
            executive_sections={name: _grounded_section(insights.get(name, []), segment_rows)
                                for name in ("objectives", "blockers", "follow_ups")},
            ai_model=APP_CONFIG.ai.model,
            prompt_version=SUMMARY_PROMPT_VERSION,
        )
    db.add(summary_row)


    for t in insights.get("tasks", []):
        source = _source_segment(t.get("transcript_timestamp"), segment_rows)
        if source is None:
            logger.warning("Skipping task without source evidence meeting=%s", meeting.id)
            continue
        if not t.get("source_quote"):
            logger.warning("Skipping task without exact source quote meeting=%s", meeting.id)
            continue
        if not _supported_by_source(t["title"], source, t.get("source_quote")):
            logger.warning("Skipping task unsupported by cited speech meeting=%s segment=%s", meeting.id, source.id)
            continue
        priority = t["priority"]
        proposed_name = (t.get("assignee_name") or "").strip()
        matches = members_by_name.get(proposed_name.casefold(), [])
        assignee = matches[0] if len(matches) == 1 and proposed_name.casefold() in source.text.casefold() else None
        db.add(
            Task(
                meeting_id=meeting.id,
                title=t["title"],
                assignee_id=assignee.id if assignee else None,
                assignee_name=assignee.name if assignee else None,
                due_date=t.get("due_date"),
                priority=TaskPriority(priority),
                transcript_timestamp=format_timestamp(source.start_time),
                source_segment_id=source.id,
                source_speaker=source.speaker,
                source_quote=t["source_quote"],
                extraction_confidence=0.9,
                ai_model=APP_CONFIG.ai.model,
                prompt_version=TASK_EXTRACTION_PROMPT_VERSION,
            )
        )

    for d in insights.get("decisions", []):
        source = _source_segment(d.get("transcript_timestamp"), segment_rows)
        if source is None:
            logger.warning("Skipping decision without source evidence meeting=%s", meeting.id)
            continue
        if not d.get("source_quote"):
            logger.warning("Skipping decision without exact source quote meeting=%s", meeting.id)
            continue
        if not _supported_by_source(d["topic"] + " " + d["outcome"], source, d.get("source_quote")):
            logger.warning("Skipping decision unsupported by cited speech meeting=%s segment=%s", meeting.id, source.id)
            continue
        db.add(
            Decision(
                meeting_id=meeting.id,
                topic=d["topic"],
                outcome=d["outcome"],
                transcript_timestamp=format_timestamp(source.start_time),
                source_segment_id=source.id,
                source_speaker=source.speaker,
                source_quote=d["source_quote"],
                extraction_confidence=0.9,
                ai_model=APP_CONFIG.ai.model,
                prompt_version=DECISION_EXTRACTION_PROMPT_VERSION,
            )
        )

    summary_row.executive_sections["key_decisions"] = [
        {"text": row.outcome, "speaker": row.source_speaker,
         "timestamp": row.transcript_timestamp, "source_quote": row.source_quote,
         "source_segment_id": str(row.source_segment_id)}
        for row in db.new if isinstance(row, Decision) and row.meeting_id == meeting.id
    ]
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(summary_row, "executive_sections")

    meeting.status = MeetingStatus.completed
    meeting.failure_reason = None
    if not meeting.workspace.is_demo:
        track_event(db, "meeting_completed", meeting.created_by, meeting.workspace_id)
    db.add(
        Notification(
            user_id=meeting.created_by,
            type=NotificationType.meeting_processed,
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

        # If this is a live meeting session, delegate to process_live_meeting
        if getattr(meeting, "source", None) == "live" or (not meeting.audio_url and getattr(meeting, "native_meeting_id", None)):
            db.close()
            process_live_meeting(meeting_id)
            return

        meeting = _claim(db, meeting.id)
        if meeting is None:
            logger.info("Skipping duplicate or non-queued meeting=%s", meeting_id)
            return

        if not meeting.audio_url:
            raise ValueError(f"Meeting {meeting.id} has no audio recording uploaded.")

        audio_path = resolve_local_path(meeting.audio_url)


        # 1. Transcription + speaker segmentation with Redis rate limiting & chunking
        transcription = transcribe_audio_with_metadata(audio_path, meeting_id=str(meeting.id))
        raw_segments = transcription.segments
        if not raw_segments:
            raise ValueError("Transcription returned no segments")
        meeting.status = MeetingStatus.transcribed
        meeting.processing_updated_at = datetime.now(timezone.utc)
        db.commit()

        # 2. Shared downstream embedding and intelligence extraction
        process_transcript_intelligence(db, meeting, raw_segments, transcription)

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
        if retries < max_retries:
            meeting = db.get(Meeting, uuid.UUID(meeting_id))
            if meeting is not None:
                meeting.status = MeetingStatus.queued
                db.commit()
        else:
            try:
                meeting = db.get(Meeting, uuid.UUID(meeting_id))
                if meeting is not None:
                    meeting.status = MeetingStatus.failed
                    meeting.failure_reason = "AI provider rate limit exceeded after automatic retries. Please retry."
                    db.commit()
            except Exception as save_err:
                logger.error("Failed saving final rate limit failure status: %s", save_err)
        raise rate_exc

    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process meeting %s", meeting_id)
        try:
            db.rollback()
            meeting = db.get(Meeting, uuid.UUID(meeting_id))
            if meeting is not None:
                meeting.status = MeetingStatus.failed
                meeting.failure_reason = f"{type(exc).__name__}: {str(exc)[:700]}"
                logger.error("Processing failure meeting=%s workspace=%s ai=%s/%s transcription=%s/%s retries=%s",
                             meeting.id, meeting.workspace_id, APP_CONFIG.ai.provider, APP_CONFIG.ai.model,
                             APP_CONFIG.transcription.provider, APP_CONFIG.transcription.model,
                             getattr(self.request, "retries", 0))
                db.add(
                    Notification(
                        user_id=meeting.created_by,
                        type=NotificationType.meeting_failed,
                        meeting_id=meeting.id,
                    )
                )
                db.commit()
        except Exception as save_err:
            logger.error("Failed saving meeting failure status: %s", save_err)
    finally:
        db.close()


@celery_app.task(
    name="process_live_meeting",
    bind=True,
    autoretry_for=(RateLimitError,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=5,
)
def process_live_meeting(self, meeting_id: str) -> None:
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, uuid.UUID(meeting_id))
        if meeting is None:
            logger.error("Live Meeting %s not found, aborting processing", meeting_id)
            return

        meeting = _claim(db, meeting.id)
        if meeting is None:
            logger.info("Skipping duplicate or non-queued live meeting=%s", meeting_id)
            return

        # Keep Vexa's confirmed speaker attribution and recording timeline.
        # Local recording transcription is a recovery path when no turns survived.
        db_segs = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.meeting_id == meeting.id)
            .order_by(TranscriptSegment.start_time)
            .all()
        )
        raw_segments = [
            {"speaker": s.speaker, "start_time": s.start_time, "end_time": s.end_time,
             "text": s.text, "language_code": s.language_code}
            for s in db_segs
        ]
        transcription = None
        if not raw_segments and meeting.audio_url:
            try:
                audio_path = resolve_local_path(meeting.audio_url)
                transcription = transcribe_audio_with_metadata(audio_path, meeting_id=str(meeting.id))
                raw_segments = transcription.segments
            except Exception as e:
                logger.warning("Whisper transcription of live audio failed: %s", e)

        if not raw_segments:
            db_segs = (
                db.query(TranscriptSegment)
                .filter(TranscriptSegment.meeting_id == meeting.id)
                .order_by(TranscriptSegment.start_time)
                .all()
            )
            raw_segments = [
                {"speaker": s.speaker, "start_time": s.start_time, "end_time": s.end_time,
                 "text": s.text, "language_code": s.language_code}
                for s in db_segs
            ]


        if not raw_segments:
            raise ValueError("Live capture ended without a transcript or audio recording")
        meeting.status = MeetingStatus.transcribed
        meeting.processing_updated_at = datetime.now(timezone.utc)
        db.commit()

        # 2. Shared downstream embedding and intelligence extraction
        process_transcript_intelligence(db, meeting, raw_segments, transcription)

    except RateLimitError as rate_exc:
        db.rollback()
        retries = getattr(self.request, "retries", 0)
        max_retries = getattr(self, "max_retries", 5)
        logger.warning(
            "Rate limit encountered for live meeting %s (retry %d/%d)",
            meeting_id,
            retries,
            max_retries,
        )
        if retries < max_retries:
            meeting = db.get(Meeting, uuid.UUID(meeting_id))
            if meeting is not None:
                meeting.status = MeetingStatus.queued
                db.commit()
        else:
            try:
                meeting = db.get(Meeting, uuid.UUID(meeting_id))
                if meeting is not None:
                    meeting.status = MeetingStatus.failed
                    meeting.failure_reason = "AI provider rate limit exceeded during live meeting analysis."
                    db.commit()
            except Exception as save_err:
                logger.error("Failed saving rate limit failure status: %s", save_err)
        raise rate_exc

    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process live meeting %s", meeting_id)
        try:
            db.rollback()
            meeting = db.get(Meeting, uuid.UUID(meeting_id))
            if meeting is not None:
                meeting.status = MeetingStatus.failed
                err_msg = str(exc)
                meeting.failure_reason = err_msg
                db.add(
                    Notification(
                        user_id=meeting.created_by,
                        type=NotificationType.meeting_failed,
                        meeting_id=meeting.id,
                    )
                )
                db.commit()
        except Exception as save_err:
            logger.error("Failed saving live meeting failure status: %s", save_err)
    finally:
        db.close()
