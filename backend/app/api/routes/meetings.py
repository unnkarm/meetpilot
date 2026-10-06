import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload


from app.api.deps import get_current_user, get_meeting_for_member
from app.core.app_config import APP_CONFIG
from app.database.session import get_db
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus, MeetingSummary
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.meeting import (
    DecisionOut,
    MeetingCreateResponse,
    MeetingDetail,
    MeetingListItem,
    MeetingSummaryOut,
    ParticipantOut,
    TaskOut,
    TranscriptSegmentOut,
)
from app.services.storage import get_storage_provider, save_upload
from app.services.product_events import track_event
from app.workers.meeting_processor import process_meeting

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


def _can_retry(meeting: Meeting) -> bool:
    if meeting.status == MeetingStatus.failed:
        return True
    active = meeting.status in (MeetingStatus.processing, MeetingStatus.transcribing,
                                MeetingStatus.transcribed, MeetingStatus.embedding, MeetingStatus.analyzing)
    return active and (meeting.processing_updated_at is None or
        meeting.processing_updated_at < datetime.now(timezone.utc) - timedelta(minutes=APP_CONFIG.stale_processing_minutes))


@router.post("/upload", response_model=MeetingCreateResponse, status_code=status.HTTP_201_CREATED)
def upload_meeting(
    workspace_id: uuid.UUID = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Meeting:
    # Confirms membership before accepting the upload.
    membership = db.get(WorkspaceMember, (workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
    workspace = db.get(Workspace, workspace_id)
    if workspace and workspace.is_demo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload real meetings to a non-demo workspace")

    meeting = Meeting(
        workspace_id=workspace_id,
        title=title,
        status=MeetingStatus.queued,
        created_by=current_user.id,
    )
    db.add(meeting)
    db.flush()

    try:
        audio_url = save_upload(file, meeting.id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    meeting.audio_url = audio_url

    # The uploader is tagged as a participant by default; others can be added
    # once diarization runs, or manually via a future endpoint.
    db.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            user_id=current_user.id,
            name=current_user.name,
            avatar_url=current_user.avatar_url,
            role=None,
        )
    )

    upload_number = db.query(Meeting).filter(Meeting.created_by == current_user.id, Meeting.source == "upload").count()
    if upload_number == 1:
        track_event(db, "first_meeting_uploaded", current_user.id, workspace_id, once=True)
    elif upload_number == 2:
        track_event(db, "second_meeting_uploaded", current_user.id, workspace_id, once=True)

    db.commit()
    db.refresh(meeting)

    try:
        process_meeting.delay(str(meeting.id))
    except Exception:
        meeting.status = MeetingStatus.failed
        meeting.failure_reason = "Could not queue processing. Retry when the worker is available."
        db.commit()

    return meeting


@router.get("", response_model=list[MeetingListItem])
def list_meetings(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Meeting]:
    membership = db.get(WorkspaceMember, (workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")

    meetings = (
        db.query(Meeting)
        .options(selectinload(Meeting.participants))
        .filter(Meeting.workspace_id == workspace_id)
        .order_by(Meeting.created_at.desc())
        .all()
    )
    return [_to_list_item(m) for m in meetings]


def _to_list_item(meeting: Meeting) -> MeetingListItem:
    return MeetingListItem(
        id=meeting.id,
        title=meeting.title,
        status=meeting.status,
        source=meeting.source,
        native_meeting_id=meeting.native_meeting_id,
        duration_seconds=meeting.duration_seconds,
        created_at=meeting.created_at,
        retry_count=meeting.retry_count,
        participants=[
            ParticipantOut(name=p.name, avatar_url=p.avatar_url, role=p.role) for p in meeting.participants
        ],
    )


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingDetail:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    base = _to_list_item(meeting)
    return MeetingDetail(**base.model_dump(), audio_url=meeting.audio_url,
                         language_code=meeting.language_code, language_name=meeting.language_name,
                         language_confidence=meeting.language_confidence, is_multilingual=meeting.is_multilingual,
                         failure_reason=meeting.failure_reason, processing_updated_at=meeting.processing_updated_at,
                         retry_available=_can_retry(meeting))


@router.get("/{meeting_id}/audio")
def stream_meeting_audio(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi.responses import FileResponse, RedirectResponse
    import mimetypes

    meeting = get_meeting_for_member(meeting_id, current_user, db)
    if not meeting.audio_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No audio file recorded for this meeting")

    if meeting.audio_url.startswith("local://"):
        from app.services.storage import resolve_local_path
        local_path = resolve_local_path(meeting.audio_url)
        if not local_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found on disk")
        mime_type, _ = mimetypes.guess_type(str(local_path))
        return FileResponse(local_path, media_type=mime_type or "audio/mpeg", filename=local_path.name)
    else:
        return RedirectResponse(meeting.audio_url)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    audio_url = meeting.audio_url
    db.delete(meeting)
    db.commit()
    if audio_url and audio_url.startswith("local://"):
        get_storage_provider().delete(audio_url)


class MeetingUpdateRequest(BaseModel):
    title: str | None = None


@router.patch("/{meeting_id}", response_model=MeetingDetail)
def update_meeting(
    meeting_id: uuid.UUID,
    payload: MeetingUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingDetail:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    if payload.title is not None and payload.title.strip():
        meeting.title = payload.title.strip()
        db.commit()
        db.refresh(meeting)
    base = _to_list_item(meeting)
    return MeetingDetail(**base.model_dump(), audio_url=meeting.audio_url,
                         language_code=meeting.language_code, language_name=meeting.language_name,
                         language_confidence=meeting.language_confidence, is_multilingual=meeting.is_multilingual,
                         failure_reason=meeting.failure_reason, processing_updated_at=meeting.processing_updated_at,
                         retry_available=_can_retry(meeting))


@router.post("/{meeting_id}/retry", response_model=MeetingCreateResponse)
def retry_meeting_processing(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Meeting:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    if not _can_retry(meeting):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Meeting is still processing or already completed")
    meeting.status = MeetingStatus.queued
    meeting.failure_reason = None
    meeting.retry_count += 1
    db.commit()
    db.refresh(meeting)
    try:
        process_meeting.delay(str(meeting.id))
    except Exception:
        meeting.status = MeetingStatus.failed
        meeting.failure_reason = "Could not queue processing. Retry when the worker is available."
        db.commit()
    return meeting


@router.get("/{meeting_id}/transcript", response_model=list[TranscriptSegmentOut])
def get_transcript(
    meeting_id: uuid.UUID,

    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TranscriptSegmentOut]:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    return meeting.transcript_segments


@router.get("/{meeting_id}/summary", response_model=MeetingSummaryOut)
def get_summary(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingSummaryOut:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    if meeting.summary is None:
        if meeting.status in (MeetingStatus.queued, MeetingStatus.processing, MeetingStatus.transcribing,
                              MeetingStatus.transcribed, MeetingStatus.embedding, MeetingStatus.analyzing):
            raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Meeting is still processing")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No summary available")
    return MeetingSummaryOut(
        overview=meeting.summary.overview,
        key_takeaways=meeting.summary.key_takeaways or [],
        next_steps=meeting.summary.next_steps or [],
        executive_sections=meeting.summary.executive_sections,
        ai_model=meeting.summary.ai_model,
        prompt_version=meeting.summary.prompt_version,
    )


@router.get("/{meeting_id}/tasks", response_model=list[TaskOut])
def get_meeting_tasks(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Task]:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    return meeting.tasks


@router.get("/{meeting_id}/decisions", response_model=list[DecisionOut])
def get_meeting_decisions(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Decision]:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    return meeting.decisions


class DecisionUpdateRequest(BaseModel):
    topic: str | None = Field(default=None, min_length=3)
    outcome: str | None = Field(default=None, min_length=3)


@router.patch("/{meeting_id}/decisions/{decision_id}", response_model=DecisionOut)
def update_decision(
    meeting_id: uuid.UUID,
    decision_id: uuid.UUID,
    payload: DecisionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Decision:
    get_meeting_for_member(meeting_id, current_user, db)
    decision = db.query(Decision).filter(Decision.id == decision_id, Decision.meeting_id == meeting_id).first()
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found in this meeting")
    for key, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(decision, key, value)
    db.commit()
    db.refresh(decision)
    return decision


@router.delete("/{meeting_id}/decisions/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_decision(
    meeting_id: uuid.UUID,
    decision_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    get_meeting_for_member(meeting_id, current_user, db)
    decision = db.query(Decision).filter(Decision.id == decision_id, Decision.meeting_id == meeting_id).first()
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found in this meeting")
    db.delete(decision)
    db.commit()


class SummaryUpdateRequest(BaseModel):
    overview: str | None = Field(default=None, min_length=3)
    key_takeaways: list[str] | None = None
    next_steps: list[str] | None = None


@router.patch("/{meeting_id}/summary", response_model=MeetingSummaryOut)
def update_summary(
    meeting_id: uuid.UUID,
    payload: SummaryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingSummaryOut:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    if meeting.summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")
    for key, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(meeting.summary, key, value)
    db.commit()
    return MeetingSummaryOut.model_validate(meeting.summary, from_attributes=True)
