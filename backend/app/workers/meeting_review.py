"""Durable review generation outside the API event loop and live bot queue."""
import logging
import uuid
from datetime import datetime, timezone

from app.core.app_config import APP_CONFIG
from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.models.meeting import Meeting
from app.models.meeting_review import MeetingArtifact
from app.models.transcript import TranscriptSegment
from app.services.access_control import membership_for
from app.services.meeting_review import ReviewError, fingerprint, generate_review, sources_for_rows

logger = logging.getLogger(__name__)


def load_sources(db, meeting_id):
    return sources_for_rows(db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id)
                            .order_by(TranscriptSegment.start_time, TranscriptSegment.id).all())


def run_review(artifact_id, session_factory=SessionLocal):
    ident, token = uuid.UUID(str(artifact_id)), str(uuid.uuid4())
    with session_factory() as db:
        claimed = db.query(MeetingArtifact).filter(MeetingArtifact.id == ident, MeetingArtifact.status == "queued").update(
            {"status": "processing", "run_token": token, "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
        db.commit()
        if not claimed:
            return  # Duplicate delivery cannot run inference or replace a result.
        row = db.get(MeetingArtifact, ident, populate_existing=True)
        meeting_id, workspace_id, user_id = row.meeting_id, row.workspace_id, row.created_by
        kind, options, expected = row.kind, dict(row.options), row.source_fingerprint

        def checkpoint(index, total):
            db.expire_all()
            membership_for(db, workspace_id, user_id)
            meeting = db.get(Meeting, meeting_id, populate_existing=True)
            if meeting is None or meeting.workspace_id != workspace_id:
                raise ReviewError("Meeting is no longer available")
            updated = db.query(MeetingArtifact).filter(MeetingArtifact.id == ident,
                MeetingArtifact.status == "processing", MeetingArtifact.run_token == token).update(
                    {"updated_at": datetime.now(timezone.utc), "payload": {"progress": {"completed": index, "total": total}}},
                    synchronize_session=False)
            db.commit()
            if not updated:
                raise ReviewError("This generation was superseded by a retry")

        try:
            checkpoint(0, 0)
            sources = load_sources(db, meeting_id)
            if fingerprint(sources) != expected:
                raise ReviewError("Transcript changed after the draft was queued. Retry with current speech.")
            db.commit()  # Do not hold a read transaction while awaiting inference.
            payload = generate_review(sources, kind, options, checkpoint=checkpoint)
            checkpoint(payload["coverage"]["windows"], payload["coverage"]["windows"])
            if fingerprint(load_sources(db, meeting_id)) != expected:
                raise ReviewError("Transcript changed during generation. Retry with current speech.")
            db.query(MeetingArtifact).filter(MeetingArtifact.id == ident, MeetingArtifact.run_token == token,
                MeetingArtifact.status == "processing").update(
                    {"status": "completed", "payload": payload, "failure_reason": None,
                     "ai_model": f"{APP_CONFIG.ai.provider}:{APP_CONFIG.ai.model}", "updated_at": datetime.now(timezone.utc)},
                    synchronize_session=False)
            db.commit()
        except Exception as exc:
            db.rollback()
            reason = str(exc) if isinstance(exc, ReviewError) else "The draft could not be generated reliably. Check worker/provider configuration and retry."
            db.query(MeetingArtifact).filter(MeetingArtifact.id == ident, MeetingArtifact.run_token == token).update(
                {"status": "failed", "payload": None, "failure_reason": reason, "updated_at": datetime.now(timezone.utc)},
                synchronize_session=False)
            db.commit()
            logger.warning("Review generation failed artifact=%s workspace=%s category=%s", ident, workspace_id, type(exc).__name__)


@celery_app.task(name="generate_meeting_review", time_limit=10800, acks_late=True)
def generate_meeting_review(artifact_id: str):
    run_review(artifact_id)
