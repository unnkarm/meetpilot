import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.workspace import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceUpdate(BaseModel):
    name: str


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime


class WorkspaceInviteRequest(BaseModel):
    email: str
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
