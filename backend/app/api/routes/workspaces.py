import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_user_workspace_ids, require_role
from app.database.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceInviteRequest,
    WorkspaceMemberOut,
    WorkspaceMemberRoleUpdate,
    WorkspaceOut,
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

