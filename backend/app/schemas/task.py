import uuid
from pydantic import BaseModel

from app.models.task import TaskPriority, TaskStatus


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: str | None = None
    assignee_name: str | None = None


class TaskCreateRequest(BaseModel):
    title: str
    workspace_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    due_date: str | None = None
    priority: TaskPriority = TaskPriority.medium
    status: TaskStatus = TaskStatus.todo
    assignee_name: str | None = None
