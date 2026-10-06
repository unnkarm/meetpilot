"""Selective, source-backed memory from live meeting speech."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class PilotMemoryKind(str, enum.Enum):
    commitment = "commitment"
    deadline = "deadline"
    fact = "fact"
    important_context = "important_context"


class PilotMemory(Base):
    __tablename__ = "pilot_memories"
    __table_args__ = (UniqueConstraint("source_segment_id", "kind", name="uq_pilot_memory_source_kind"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_segment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transcript_segments.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[PilotMemoryKind] = mapped_column(Enum(PilotMemoryKind), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_speaker: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
