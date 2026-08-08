import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload


from app.api.deps import get_current_user, get_meeting_for_member
from app.database.session import get_db
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus
from app.models.task import Task
from app.models.user import User
from app.models.workspace import WorkspaceMember
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
from app.services.storage import save_upload
from app.workers.meeting_processor import process_meeting

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


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

    meeting = Meeting(
        workspace_id=workspace_id,
        title=title,
        status=MeetingStatus.queued,
        created_by=current_user.id,
    )
    db.add(meeting)
    db.flush()

    audio_url = save_upload(file, meeting.id)
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

    db.commit()
    db.refresh(meeting)

    process_meeting.delay(str(meeting.id))

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
        duration_seconds=meeting.duration_seconds,
        created_at=meeting.created_at,
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
    return MeetingDetail(**base.model_dump(), audio_url=meeting.audio_url, failure_reason=meeting.failure_reason)


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
    if meeting.audio_url and meeting.audio_url.startswith("local://"):
        try:
            from app.services.storage import resolve_local_path
            path = resolve_local_path(meeting.audio_url)
            if path.exists():
                path.unlink()
        except Exception:
            pass
    db.delete(meeting)
    db.commit()


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
    return MeetingDetail(**base.model_dump(), audio_url=meeting.audio_url, failure_reason=meeting.failure_reason)


@router.post("/{meeting_id}/retry", response_model=MeetingCreateResponse)
def retry_meeting_processing(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Meeting:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    meeting.status = MeetingStatus.queued
    meeting.failure_reason = None
    db.commit()
    db.refresh(meeting)
    process_meeting.delay(str(meeting.id))
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
        if meeting.status in (MeetingStatus.queued, MeetingStatus.processing):
            raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Meeting is still processing")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No summary available")
    return MeetingSummaryOut(
        overview=meeting.summary.overview,
        key_takeaways=meeting.summary.key_takeaways or [],
        next_steps=meeting.summary.next_steps or [],
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
