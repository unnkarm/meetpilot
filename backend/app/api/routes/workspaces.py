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
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
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

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


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
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Workspace]:
    ids = get_user_workspace_ids(current_user, db)
    if not ids:
        return []
    return db.query(Workspace).filter(Workspace.id.in_(ids)).all()


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

    return workspace


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
    invitee = db.query(User).filter(User.email == payload.email).first()
    if invitee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered user with that email yet. Ask them to sign up first.",
        )

    existing = db.get(WorkspaceMember, (workspace_id, invitee.id))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member")

    member = WorkspaceMember(workspace_id=workspace_id, user_id=invitee.id, role=payload.role)
    db.add(member)
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
    member = db.get(WorkspaceMember, (workspace_id, user_id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

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
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    if workspace.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the workspace owner. Transfer ownership or delete workspace.",
        )

    member = db.get(WorkspaceMember, (workspace_id, user_id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in workspace")

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
    processing_meetings = sum(1 for m in meetings if m.status == MeetingStatus.processing)
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
        .filter(Meeting.workspace_id == workspace_id)
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
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Clean up local audio files for meetings in this workspace
    for meeting in workspace.meetings:
        if meeting.audio_url and not meeting.audio_url.startswith("http"):
            try:
                import os
                if os.path.exists(meeting.audio_url):
                    os.remove(meeting.audio_url)
            except Exception:
                pass

    db.delete(workspace)
    db.commit()
    return None
