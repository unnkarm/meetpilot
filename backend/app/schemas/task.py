import uuid
from datetime import date
from pydantic import BaseModel, Field, field_validator

from app.models.task import TaskPriority, TaskStatus


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: str | None = None
    assignee_name: str | None = None

    @field_validator("due_date")
    @classmethod
    def valid_due_date(cls, value: str | None) -> str | None:
        if value:
            date.fromisoformat(value)
        return value


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    workspace_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    due_date: str | None = None
    priority: TaskPriority = TaskPriority.medium
    status: TaskStatus = TaskStatus.todo
    assignee_name: str | None = None

    @field_validator("due_date")
    @classmethod
    def valid_due_date(cls, value: str | None) -> str | None:
        if value:
            date.fromisoformat(value)
        return value
