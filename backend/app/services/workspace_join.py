"""High-entropy join codes request access; only a manager grants membership."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole, WorkspaceJoinRequest
from app.services.access_control import lock_workspace_manager


def hash_join_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def rotate_join_code(db, workspace_id, actor_id):
    workspace, _ = lock_workspace_manager(db, workspace_id, actor_id)
    if workspace.is_demo:
        raise HTTPException(status_code=400, detail="Sample workspaces cannot accept join requests")
    code = secrets.token_urlsafe(24)
    workspace.join_code_hash = hash_join_code(code)
    workspace.join_code_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db.commit()
    return {"code": code, "expires_at": workspace.join_code_expires_at}


def disable_join_code(db, workspace_id, actor_id):
    workspace, _ = lock_workspace_manager(db, workspace_id, actor_id)
    workspace.join_code_hash = None
    workspace.join_code_expires_at = None
    db.commit()


def submit_join_request(db, code, user_id):
    workspace = db.query(Workspace).filter(Workspace.join_code_hash == hash_join_code(code)).with_for_update().first()
    expiry = workspace.join_code_expires_at if workspace else None
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if (workspace is None or workspace.is_demo or workspace.join_code_expires_at is None
            or expiry <= datetime.now(timezone.utc)):
        raise HTTPException(status_code=404, detail="Join code is invalid or expired")
    if db.get(WorkspaceMember, (workspace.id, user_id)) is not None:
        raise HTTPException(status_code=409, detail="You already belong to this workspace")
    request = db.query(WorkspaceJoinRequest).filter(
        WorkspaceJoinRequest.workspace_id == workspace.id, WorkspaceJoinRequest.user_id == user_id,
    ).with_for_update().first()
    if request and request.status == "rejected":
        raise HTTPException(status_code=409, detail="Your request was declined. Contact a workspace manager")
    if request is None:
        request = WorkspaceJoinRequest(workspace_id=workspace.id, user_id=user_id, status="pending")
        db.add(request)
    elif request.status == "approved":
        # A removed member needs fresh approval and cannot reuse an old decision.
        request.status = "pending"
        request.reviewed_by = None
        request.reviewed_at = None
    db.commit()
    db.refresh(request)
    return request


def review_join_request(db, workspace_id, request_id, actor_id, decision):
    # Lock serializes concurrent reviews and membership creation.
    lock_workspace_manager(db, workspace_id, actor_id)
    request = db.query(WorkspaceJoinRequest).filter(
        WorkspaceJoinRequest.id == request_id, WorkspaceJoinRequest.workspace_id == workspace_id,
    ).with_for_update().first()
    if request is None:
        raise HTTPException(status_code=404, detail="Join request not found")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="Join request has already been reviewed")
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="Invalid review decision")
    request.status = "approved" if decision == "approve" else "rejected"
    request.reviewed_by = actor_id
    request.reviewed_at = datetime.now(timezone.utc)
    if decision == "approve" and db.get(WorkspaceMember, (workspace_id, request.user_id)) is None:
        db.add(WorkspaceMember(workspace_id=workspace_id, user_id=request.user_id, role=WorkspaceRole.member))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Membership changed concurrently. Refresh and retry") from exc
    return request
