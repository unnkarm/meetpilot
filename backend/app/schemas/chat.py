import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.chat import ChatRole


class ChatRequest(BaseModel):
    question: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: ChatRole
    content: str
    cited_timestamp: str | None = None
    created_at: datetime


class ChatResponse(BaseModel):
    answer: str
    cited_timestamp: str | None = None
