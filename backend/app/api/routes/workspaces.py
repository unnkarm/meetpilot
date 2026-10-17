import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_user_workspace_ids, require_role
from app.database.session import get_db
from app.models.decision import Decision
from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task, TaskStatus
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole, WorkspaceJoinRequest
from app.services.access_control import require_manager, lock_workspace_manager, task_visibility
from app.services.workspace_join import rotate_join_code, disable_join_code, submit_join_request, review_join_request
from app.schemas.workspace import WorkspaceJoinRequestIn, WorkspaceJoinRequestOut, WorkspaceJoinReview
from app.schemas.workspace import (
    SpeakerAirtimeItem,
    WorkspaceAnalyticsOut,
    WorkspaceCreate,
    WorkspaceInviteRequest,
    WorkspaceMemberOut,
    WorkspaceMemberRoleUpdate,
    WorkspaceOut,
    WorkspaceUpdate,
)
from app.services.storage import get_storage_provider
from app.services.demo_workspace import create_demo_workspace
from app.services.product_events import track_event

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


def _workspace_out(workspace, db, user_id):
    member = db.get(WorkspaceMember, (workspace.id, user_id))
    return WorkspaceOut(**WorkspaceOut.model_validate(workspace).model_dump(exclude={"current_role"}),
                        current_role=member.role if member else WorkspaceRole.member)


def _join_out(request, db):
    user = db.get(User, request.user_id)
    workspace = db.get(Workspace, request.workspace_id)
    access_status = request.status
    if access_status == "approved" and db.get(WorkspaceMember, (request.workspace_id, request.user_id), populate_existing=True) is None:
        access_status = "removed"
    return WorkspaceJoinRequestOut(id=request.id, workspace_id=request.workspace_id,
        workspace_name=workspace.name, user_id=user.id, name=user.name, email=user.email, email_verified=user.email_verified,
        status=access_status, created_at=request.created_at)


@router.post("/join", response_model=WorkspaceJoinRequestOut, status_code=201)
def request_workspace_access(payload: WorkspaceJoinRequestIn,
                             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _join_out(submit_join_request(db, payload.code, user.id), db)


@router.get("/join-requests", response_model=list[WorkspaceJoinRequestOut])
def my_join_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(WorkspaceJoinRequest).filter(WorkspaceJoinRequest.user_id == user.id).order_by(WorkspaceJoinRequest.created_at.desc()).all()
    return [_join_out(row, db) for row in rows]


@router.post("/{workspace_id}/join-code")
def generate_join_code(workspace_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return rotate_join_code(db, workspace_id, user.id)


@router.delete("/{workspace_id}/join-code", status_code=204)
def revoke_join_code(workspace_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    disable_join_code(db, workspace_id, user.id)


@router.get("/{workspace_id}/join-requests", response_model=list[WorkspaceJoinRequestOut])
def pending_join_requests(workspace_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_manager(db, workspace_id, user.id)
    rows = db.query(WorkspaceJoinRequest).filter(WorkspaceJoinRequest.workspace_id == workspace_id,
        WorkspaceJoinRequest.status == "pending").order_by(WorkspaceJoinRequest.created_at).all()
    return [_join_out(row, db) for row in rows]


@router.post("/{workspace_id}/join-requests/{request_id}/review", response_model=WorkspaceJoinRequestOut)
def review_workspace_access(workspace_id: uuid.UUID, request_id: uuid.UUID, payload: WorkspaceJoinReview,
                             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _join_out(review_join_request(db, workspace_id, request_id, user.id, payload.decision), db)


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    workspace = Workspace(name=payload.name, owner_id=current_user.id)
    db.add(workspace)
    db.flush()

    membership = WorkspaceMember(workspace_id=workspace.id, user_id=current_user.id, role=WorkspaceRole.owner)
    db.add(membership)
    track_event(db, "workspace_created", current_user.id, workspace.id)
    db.commit()
    db.refresh(workspace)
    return _workspace_out(workspace, db, current_user.id)


@router.post("/demo", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def explore_demo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    """Create or return this user's isolated sample workspace."""
    return _workspace_out(create_demo_workspace(db, current_user), db, current_user.id)


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Workspace]:
    ids = get_user_workspace_ids(current_user, db)
    if not ids:
        return []
    return [_workspace_out(ws, db, current_user.id) for ws in db.query(Workspace).filter(Workspace.id.in_(ids)).all()]


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    _membership=Depends(require_role(WorkspaceRole.owner, WorkspaceRole.admin)),
) -> Workspace:
    """Updates workspace settings / name. Restricted to workspace owner or admin."""
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    if payload.name and payload.name.strip():
        workspace.name = payload.name.strip()
        db.commit()
        db.refresh(workspace)

    return _workspace_out(workspace, db, _membership.user_id)


@router.post(
    "/{workspace_id}/invite",
    response_model=WorkspaceMemberOut,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    workspace_id: uuid.UUID,
    payload: WorkspaceInviteRequest,
    db: Session = Depends(get_db),
    _membership=Depends(require_role(WorkspaceRole.owner, WorkspaceRole.admin)),
) -> WorkspaceMemberOut:
    _, _membership = lock_workspace_manager(db, workspace_id, _membership.user_id)
    if payload.role == WorkspaceRole.owner or (payload.role == WorkspaceRole.admin and _membership.role != WorkspaceRole.owner):
        raise HTTPException(status_code=403, detail="Only the owner may appoint managers; ownership cannot be assigned here")
    invitees = db.query(User).filter(func.lower(User.email) == payload.email.strip().casefold()).all()
    if not invitees:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered user with that email yet. Ask them to sign up first.",
        )
    if len(invitees) > 1:
        raise HTTPException(status_code=409, detail="Multiple accounts match that email. Ask the person to request access with a join code")
    invitee = invitees[0]
    if not invitee.email_verified:
        raise HTTPException(status_code=422, detail="Email invitations require a verified account email. Ask the user to request access with a join code instead")

    existing = db.get(WorkspaceMember, (workspace_id, invitee.id))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member")

    member = WorkspaceMember(workspace_id=workspace_id, user_id=invitee.id, role=payload.role)
    db.add(member)
    track_event(db, "team_member_invited", _membership.user_id, workspace_id)
    db.commit()

    return WorkspaceMemberOut(
        user_id=invitee.id, role=member.role, name=invitee.name, email=invitee.email, avatar_url=invitee.avatar_url
    )


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
def list_members(
    workspace_id: uuid.UUID,
    db: Session = Depends(get_db),
    _membership=Depends(require_role(WorkspaceRole.owner, WorkspaceRole.admin, WorkspaceRole.member)),
) -> list[WorkspaceMemberOut]:
    rows = (
        db.query(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .all()
    )
    return [
        WorkspaceMemberOut(user_id=u.id, role=m.role, name=u.name, email=u.email, avatar_url=u.avatar_url)
        for m, u in rows
    ]


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberOut)
def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: WorkspaceMemberRoleUpdate,
    db: Session = Depends(get_db),
    _membership=Depends(require_role(WorkspaceRole.owner, WorkspaceRole.admin)),
) -> WorkspaceMemberOut:
    workspace, _membership = lock_workspace_manager(db, workspace_id, _membership.user_id)
    member = db.get(WorkspaceMember, (workspace_id, user_id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if user_id == workspace.owner_id or payload.role == WorkspaceRole.owner:
        raise HTTPException(status_code=403, detail="Workspace ownership cannot be changed through member roles")
    if _membership.role != WorkspaceRole.owner and (member.role == WorkspaceRole.admin or payload.role == WorkspaceRole.admin):
        raise HTTPException(status_code=403, detail="Only the owner may change manager roles")

    member.role = payload.role
    db.commit()

    user = db.get(User, user_id)
    return WorkspaceMemberOut(user_id=user.id, role=member.role, name=user.name, email=user.email, avatar_url=user.avatar_url)


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _membership=Depends(require_role(WorkspaceRole.owner, WorkspaceRole.admin)),
):
    """Removes a user membership from the workspace. Restricted to workspace owner or admin."""
    workspace, _membership = lock_workspace_manager(db, workspace_id, current_user.id)
    if workspace.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the workspace owner. Transfer ownership or delete workspace.",
        )

    member = db.get(WorkspaceMember, (workspace_id, user_id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in workspace")

    if member.role == WorkspaceRole.admin and _membership.role != WorkspaceRole.owner:
        raise HTTPException(status_code=403, detail="Only the owner may remove a manager")

    db.delete(member)
    db.commit()
    return None


@router.get("/{workspace_id}/analytics", response_model=WorkspaceAnalyticsOut)
def get_workspace_analytics(
    workspace_id: uuid.UUID,
    db: Session = Depends(get_db),
    _membership=Depends(require_role(WorkspaceRole.owner, WorkspaceRole.admin, WorkspaceRole.member)),
) -> WorkspaceAnalyticsOut:
    """Aggregates real-time meeting intelligence metrics and speaker distribution from PostgreSQL."""
    # 1. Meeting status counts & speaking durations
    meetings = db.query(Meeting).filter(Meeting.workspace_id == workspace_id).all()
    total_meetings = len(meetings)
    completed_meetings = sum(1 for m in meetings if m.status == MeetingStatus.completed)
    processing_meetings = sum(1 for m in meetings if m.status in (
        MeetingStatus.processing, MeetingStatus.transcribing, MeetingStatus.transcribed,
        MeetingStatus.embedding, MeetingStatus.analyzing))
    queued_meetings = sum(1 for m in meetings if m.status == MeetingStatus.queued)
    failed_meetings = sum(1 for m in meetings if m.status == MeetingStatus.failed)

    total_speaking_seconds = sum(m.duration_seconds or 0 for m in meetings if m.status == MeetingStatus.completed)
    total_speaking_hours = round(total_speaking_seconds / 3600.0, 2)
    avg_duration_minutes = (
        round((total_speaking_seconds / completed_meetings) / 60.0, 1) if completed_meetings > 0 else 0.0
    )

    # 2. Consensus Decisions count
    total_decisions = (
        db.query(func.count(Decision.id))
        .join(Meeting, Meeting.id == Decision.meeting_id)
        .filter(Meeting.workspace_id == workspace_id)
        .scalar()
        or 0
    )

    # 3. Action items & completion breakdown
    tasks = (
        db.query(Task)
        .join(Meeting, Meeting.id == Task.meeting_id)
        .filter(Meeting.workspace_id == workspace_id, task_visibility(_membership.user_id))
        .all()
    )
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.done)
    in_progress_tasks = sum(1 for t in tasks if t.status == TaskStatus.doing)
    todo_tasks = sum(1 for t in tasks if t.status == TaskStatus.todo)
    task_completion_rate = (
        round((completed_tasks / total_tasks) * 100.0, 1) if total_tasks > 0 else 0.0
    )

    # 4. Speaker Airtime & Participation distribution from real transcript segments
    segment_rows = (
        db.query(TranscriptSegment.speaker, TranscriptSegment.start_time, TranscriptSegment.end_time)
        .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
        .filter(Meeting.workspace_id == workspace_id)
        .all()
    )

    speaker_seconds_map: dict[str, float] = {}
    speaker_turns_map: dict[str, int] = {}
    total_diarized_seconds = 0.0

    for speaker, start, end in segment_rows:
        spk = (speaker or "Speaker 1").strip()
        dur = max(0.0, float(end or 0.0) - float(start or 0.0))
        speaker_seconds_map[spk] = speaker_seconds_map.get(spk, 0.0) + dur
        speaker_turns_map[spk] = speaker_turns_map.get(spk, 0) + 1
        total_diarized_seconds += dur

    speakers_distribution: list[SpeakerAirtimeItem] = []
    for spk, dur in sorted(speaker_seconds_map.items(), key=lambda x: x[1], reverse=True):
        pct = int(round((dur / total_diarized_seconds) * 100)) if total_diarized_seconds > 0 else 0
        speakers_distribution.append(
            SpeakerAirtimeItem(
                speaker=spk,
                duration_seconds=round(dur, 1),
                percentage=pct,
                turn_count=speaker_turns_map.get(spk, 0),
            )
        )

    return WorkspaceAnalyticsOut(
        workspace_id=workspace_id,
        total_meetings=total_meetings,
        completed_meetings=completed_meetings,
        processing_meetings=processing_meetings,
        queued_meetings=queued_meetings,
        failed_meetings=failed_meetings,
        total_speaking_seconds=int(total_speaking_seconds),
        total_speaking_hours=total_speaking_hours,
        avg_meeting_duration_minutes=avg_duration_minutes,
        total_decisions=total_decisions,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        todo_tasks=todo_tasks,
        task_completion_rate=task_completion_rate,
        speakers_distribution=speakers_distribution,
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: uuid.UUID,
    db: Session = Depends(get_db),
    _membership=Depends(require_role(WorkspaceRole.owner)),
):
    """Deletes a workspace, its meetings, audio recordings, and member associations. Restricted to workspace owner."""
    workspace, _membership = lock_workspace_manager(db, workspace_id, _membership.user_id)
    if workspace.owner_id != _membership.user_id:
        raise HTTPException(status_code=403, detail="Only the registered workspace owner may delete it")

    audio_urls = [meeting.audio_url for meeting in workspace.meetings if meeting.audio_url and meeting.audio_url.startswith("local://")]
    db.delete(workspace)
    db.commit()
    storage = get_storage_provider()
    for audio_url in audio_urls:
        storage.delete(audio_url)
    return None
