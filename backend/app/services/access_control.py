"""Shared workspace permissions. Identity labels never grant permissions."""
import uuid

from fastapi import HTTPException
from sqlalchemy import exists, or_, and_, select
from sqlalchemy.orm import Session

from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.meeting import Meeting
from app.models.task import Task

MANAGER_ROLES = {WorkspaceRole.owner, WorkspaceRole.admin}


def membership_for(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID):
    member = db.get(WorkspaceMember, (workspace_id, user_id), populate_existing=True)
    if member is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return member


def is_manager(member) -> bool:
    return member is not None and member.role in MANAGER_ROLES


def require_manager(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID):
    member = membership_for(db, workspace_id, user_id)
    if not is_manager(member):
        raise HTTPException(status_code=403, detail="Only workspace managers can perform this action")
    return member


def lock_workspace_manager(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Serialize membership changes, then check the actor's current authority."""
    require_manager(db, workspace_id, user_id)
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).with_for_update().first()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace, require_manager(db, workspace_id, user_id)


def require_meeting_control(db: Session, meeting, user_id: uuid.UUID):
    member = membership_for(db, meeting.workspace_id, user_id)
    if not is_manager(member) and meeting.created_by != user_id:
        raise HTTPException(status_code=403, detail="Only the meeting creator or a manager can control this meeting")


def task_visibility(user_id: uuid.UUID):
    """SQL predicate used before retrieval, limits, or LLM prompts."""
    membership = exists(select(WorkspaceMember.user_id).where(
        WorkspaceMember.workspace_id == Meeting.workspace_id,
        WorkspaceMember.user_id == user_id,
    ))
    manager = exists(select(WorkspaceMember.user_id).where(
        WorkspaceMember.workspace_id == Meeting.workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.role.in_(list(MANAGER_ROLES)),
    ))
    return and_(membership, or_(manager, Task.assignee_id == user_id))


def require_task_update(db: Session, task, user_id: uuid.UUID, fields: set[str]):
    member = membership_for(db, task.meeting.workspace_id, user_id)
    if is_manager(member):
        return
    if task.assignee_id != user_id or not fields.issubset({"status"}):
        raise HTTPException(status_code=403, detail="Teammates may only update the status of their assigned tasks")
