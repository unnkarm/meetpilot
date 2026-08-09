import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_meeting_for_member
from app.api.routes.meetings import _to_list_item
from app.database.session import get_db
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.meeting import LiveMeetingStartRequest, MeetingDetail
from app.services.vexa_client import (
    extract_google_meet_code,
    listen_live_transcript_stream,
    start_google_meet_bot,
    stop_google_meet_bot,
)
from app.workers.meeting_processor import process_live_meeting

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meetings/live", tags=["live-meetings"])


@router.post("/start", response_model=MeetingDetail, status_code=status.HTTP_201_CREATED)
async def start_live_meeting(
    payload: LiveMeetingStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingDetail:
    """Dispatches a Vexa bot to join a Google Meet room and streams transcripts in real-time."""
    # 1. Tenant Isolation: Confirm user is a member of the workspace
    membership = db.get(WorkspaceMember, (payload.workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    # 2. Extract and validate Google Meet code
    clean_code = extract_google_meet_code(payload.meeting_url)
    title = (payload.title or "").strip() or f"Google Meet ({clean_code})"

    # 3. Create meeting row in database with source='live' and status='in_progress'
    meeting = Meeting(
        workspace_id=payload.workspace_id,
        title=title,
        source="live",
        native_meeting_id=clean_code,
        status=MeetingStatus.in_progress,
        created_by=current_user.id,
    )
    db.add(meeting)
    db.flush()

    # Tag user as participant
    db.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            user_id=current_user.id,
            name=current_user.name,
            avatar_url=current_user.avatar_url,
            role="Host",
        )
    )
    db.commit()
    db.refresh(meeting)

    # 4. Dispatch Vexa Bot via REST
    try:
        start_res = start_google_meet_bot(clean_code, bot_name="MeetPilot AI Bot", transcribe_enabled=True)
        if isinstance(start_res, dict) and "id" in start_res:
            meeting.vexa_bot_id = str(start_res["id"])
            db.commit()
            db.refresh(meeting)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed dispatching Vexa bot for Google Meet %s", clean_code)
        meeting.status = MeetingStatus.failed
        meeting.failure_reason = f"Failed dispatching meeting bot: {exc}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed dispatching live meeting bot: {exc}",
        )

    # 5. Launch asynchronous background WebSocket consumer for live transcript ingestion
    try:
        asyncio.create_task(listen_live_transcript_stream(meeting.id, clean_code))
    except Exception as stream_exc:
        logger.warning("Could not launch background WebSocket stream listener: %s", stream_exc)

    base = _to_list_item(meeting)
    return MeetingDetail(**base.model_dump(), audio_url=meeting.audio_url, failure_reason=meeting.failure_reason)


@router.post("/{meeting_id}/stop", response_model=MeetingDetail)
def stop_live_meeting(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingDetail:
    """Tells Vexa's bot to leave the call and enqueues the meeting into the downstream Celery pipeline."""
    meeting = get_meeting_for_member(meeting_id, current_user, db)

    # 1. Stop Vexa bot
    if meeting.native_meeting_id:
        try:
            stop_google_meet_bot(meeting.native_meeting_id)
        except Exception as stop_exc:
            logger.warning("Error stopping Vexa bot for %s: %s", meeting.native_meeting_id, stop_exc)

    # 2. Mark meeting status as queued and enqueue downstream Celery extraction pipeline
    meeting.status = MeetingStatus.queued
    meeting.failure_reason = None
    db.commit()
    db.refresh(meeting)

    process_live_meeting.delay(str(meeting.id))

    base = _to_list_item(meeting)
    return MeetingDetail(**base.model_dump(), audio_url=meeting.audio_url, failure_reason=meeting.failure_reason)
