import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.workspace import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime


class WorkspaceInviteRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.member


class WorkspaceMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role: WorkspaceRole
    name: str
    email: str
    avatar_url: str | None = None


class WorkspaceMemberRoleUpdate(BaseModel):
    role: WorkspaceRole
