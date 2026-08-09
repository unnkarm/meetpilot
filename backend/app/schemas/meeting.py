import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.meeting import MeetingStatus
from app.models.task import TaskPriority, TaskStatus


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    avatar_url: str | None = None
    role: str | None = None


class MeetingCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: MeetingStatus
    created_at: datetime


class LiveMeetingStartRequest(BaseModel):
    workspace_id: uuid.UUID
    meeting_url: str
    title: str | None = None


class MeetingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: MeetingStatus
    source: str = "upload"
    native_meeting_id: str | None = None
    duration_seconds: int | None = None
    created_at: datetime
    participants: list[ParticipantOut] = []


class MeetingDetail(MeetingListItem):
    audio_url: str | None = None
    failure_reason: str | None = None


class TranscriptSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    speaker: str
    start_time: float
    end_time: float
    text: str


class MeetingSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overview: str | None = None
    key_takeaways: list[str] = []
    next_steps: list[str] = []


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    assignee_name: str | None = None
    due_date: str | None = None
    priority: TaskPriority
    status: TaskStatus
    transcript_timestamp: str | None = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: str
    outcome: str
    transcript_timestamp: str | None = None
