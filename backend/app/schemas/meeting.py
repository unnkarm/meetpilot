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
    retry_count: int = 0


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
    language_code: str | None = None
    language_name: str | None = None
    language_confidence: float | None = None
    is_multilingual: bool = False
    failure_reason: str | None = None
    processing_updated_at: datetime | None = None
    retry_available: bool = False


class TranscriptSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    speaker: str
    start_time: float
    end_time: float
    text: str
    language_code: str | None = None


class MeetingSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overview: str | None = None
    key_takeaways: list[str] = []
    next_steps: list[str] = []
    executive_sections: dict[str, list[dict]] | None = None
    ai_model: str | None = None
    prompt_version: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    assignee_name: str | None = None
    due_date: str | None = None
    priority: TaskPriority
    status: TaskStatus
    transcript_timestamp: str | None = None
    source_segment_id: uuid.UUID | None = None
    source_speaker: str | None = None
    source_quote: str | None = None
    extraction_confidence: float | None = None
    ai_model: str | None = None
    prompt_version: str | None = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: str
    outcome: str
    transcript_timestamp: str | None = None
    source_segment_id: uuid.UUID | None = None
    source_speaker: str | None = None
    source_quote: str | None = None
    extraction_confidence: float | None = None
    ai_model: str | None = None
    prompt_version: str | None = None
