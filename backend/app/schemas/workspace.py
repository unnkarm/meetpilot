import uuid
from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.workspace import WorkspaceRole


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)


class WorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    is_demo: bool = False
    current_role: WorkspaceRole = WorkspaceRole.member
    created_at: datetime


class WorkspaceInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    model_config = ConfigDict(extra="forbid")
    role: WorkspaceRole


class WorkspaceJoinRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=16, max_length=128)


class WorkspaceJoinRequestOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str
    user_id: uuid.UUID
    name: str
    email: str
    email_verified: bool = False
    status: Literal["pending", "approved", "rejected", "removed"]
    created_at: datetime


class WorkspaceJoinReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]


class SpeakerAirtimeItem(BaseModel):
    speaker: str
    duration_seconds: float
    percentage: int
    turn_count: int


class WorkspaceAnalyticsOut(BaseModel):
    workspace_id: uuid.UUID
    total_meetings: int
    completed_meetings: int
    processing_meetings: int
    queued_meetings: int
    failed_meetings: int
    total_speaking_seconds: int
    total_speaking_hours: float
    avg_meeting_duration_minutes: float
    total_decisions: int
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    task_completion_rate: float
    speakers_distribution: List[SpeakerAirtimeItem]
