import logging
import uuid
import json
from pathlib import Path

import redis
from fastapi.responses import FileResponse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_meeting_for_member
from app.api.routes.meetings import _to_list_item
from app.database.session import get_db
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.meeting import LiveMeetingStartRequest, MeetingDetail
from app.services.native_meeting import parse_meeting_target
from app.workers.vexa_meeting import run_vexa_meeting_bot_task
from app.services.vexa_client import VexaClient, VexaError
import asyncio
from app.workers.meeting_processor import process_live_meeting
from app.core.config import settings
from app.services.meeting_language import display_script
from app.services.access_control import require_meeting_control

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meetings/live", tags=["live-meetings"])


@router.get("/{meeting_id}/bot-status")
def bot_status(meeting_id: uuid.UUID, current_user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> dict:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    client = redis.Redis.from_url(settings.REDIS_URL)
    raw = client.get(f"native-meeting:{meeting_id}:status")
    return json.loads(raw) if raw else {"state": meeting.status.value, "text": meeting.failure_reason or "Bot is queued"}


@router.get("/{meeting_id}/bot-diagnostics")
def bot_diagnostics(meeting_id: uuid.UUID, current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    screenshot = Path(settings.STORAGE_DIR) / "bot_diagnostics" / str(meeting.workspace_id) / f"{meeting.id}.png"
    if not screenshot.is_file():
        raise HTTPException(status_code=404, detail="No bot screenshot has been captured for this meeting")
    return FileResponse(screenshot, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/start", response_model=MeetingDetail, status_code=status.HTTP_201_CREATED)
async def start_live_meeting(
    payload: LiveMeetingStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingDetail:
    """Queue the upstream Vexa engine using this workspace's credentials."""
    # 1. Tenant Isolation: Confirm user is a member of the workspace
    membership = db.get(WorkspaceMember, (payload.workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    try:
        script = display_script(payload.transcription_language, payload.display_script)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 2. Restrict browser navigation to known meeting hosts.
    try:
        target = parse_meeting_target(payload.meeting_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        await asyncio.to_thread(VexaClient(payload.workspace_id).preflight)
    except Exception as exc:
        logger.warning("Vexa preflight failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Local Vexa engine is unavailable. Start Docker Compose and check Vexa health.") from exc
    title = (payload.title or "").strip() or f"{target.platform.replace('_', ' ').title()} ({target.native_id})"

    # 3. Create meeting row in database with source='live' and status='in_progress'
    meeting = Meeting(
        workspace_id=payload.workspace_id,
        title=title,
        source="live",
        native_meeting_id=target.native_id,
        status=MeetingStatus.in_progress,
        transcription_language=payload.transcription_language,
        display_script=script,
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

    # 4. Dispatch Vexa's bridge on its own queue; a meeting cannot block uploads.
    try:
        run_vexa_meeting_bot_task.apply_async(
            args=[str(meeting.id), target.url, "MeetPilot AI Bot"], queue="meeting_bot",
        )
    except Exception as exc:
        logger.exception("Could not queue Vexa meeting bot meeting=%s", meeting.id)
        db.delete(meeting)
        db.commit()
        raise HTTPException(status_code=503, detail="Vexa bridge worker is unavailable") from exc

    base = _to_list_item(meeting)
    return MeetingDetail(**base.model_dump(), audio_url=meeting.audio_url, failure_reason=meeting.failure_reason,
                         capture_failure_reason=meeting.capture_failure_reason,
                         transcription_language=meeting.transcription_language, display_script=meeting.display_script,
                         language_code=meeting.language_code, language_name=meeting.language_name,
                         language_confidence=meeting.language_confidence, is_multilingual=meeting.is_multilingual)


@router.post("/{meeting_id}/stop", response_model=MeetingDetail)
def stop_live_meeting(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingDetail:
    """Signal Vexa to leave, then process the persisted local transcript."""
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    require_meeting_control(db, meeting, current_user.id)

    # The bot observes this status, flushes its speech buffers, and exits.
    meeting.status = MeetingStatus.queued
    meeting.failure_reason = None
    db.commit()
    db.refresh(meeting)

    # Fallback if the bot failed before its normal shutdown path. _claim keeps
    # duplicate deliveries from processing the meeting twice.
    process_live_meeting.apply_async(args=[str(meeting.id)], countdown=120)

    base = _to_list_item(meeting)
    return MeetingDetail(**base.model_dump(), audio_url=meeting.audio_url, failure_reason=meeting.failure_reason,
                         capture_failure_reason=meeting.capture_failure_reason,
                         transcription_language=meeting.transcription_language, display_script=meeting.display_script,
                         language_code=meeting.language_code, language_name=meeting.language_name,
                         language_confidence=meeting.language_confidence, is_multilingual=meeting.is_multilingual)
