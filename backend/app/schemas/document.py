import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    failure_reason: Optional[str] = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentOut
    message: str


class KnowledgeCitation(BaseModel):
    type: str  # "document" | "meeting"
    title: str
    document_id: Optional[str] = None
    meeting_id: Optional[str] = None
    page_number: Optional[int] = None
    timestamp: Optional[str] = None
    speaker: Optional[str] = None
    snippet: str


class KnowledgeChatRequest(BaseModel):
    workspace_id: uuid.UUID
    question: str


class KnowledgeChatResponse(BaseModel):
    answer: str
    citations: List[KnowledgeCitation]
