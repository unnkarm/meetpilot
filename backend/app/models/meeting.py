import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class MeetingStatus(str, enum.Enum):
    in_progress = "in_progress"
    queued = "queued"
    processing = "processing"
    transcribing = "transcribing"
    transcribed = "transcribed"
    embedding = "embedding"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="upload", nullable=False)
    native_meeting_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    language_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    language_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_multilingual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[MeetingStatus] = mapped_column(Enum(MeetingStatus), default=MeetingStatus.queued, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", back_populates="meetings")
    participants = relationship(
        "MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan", passive_deletes=True
    )
    transcript_segments = relationship(
        "TranscriptSegment",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TranscriptSegment.start_time",
    )
    summary = relationship(
        "MeetingSummary", back_populates="meeting", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )
    tasks = relationship("Task", back_populates="meeting", cascade="all, delete-orphan", passive_deletes=True)
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan", passive_deletes=True)
    chat_messages = relationship(
        "ChatMessage",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessage.created_at",
    )
    notifications = relationship(
        "Notification",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MeetingParticipant(Base):
    """A participant tag on a meeting. May map to a registered user, or just be a free-text name."""

    __tablename__ = "meeting_participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    identity_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    meeting = relationship("Meeting", back_populates="participants")


class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_takeaways: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    next_steps: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    executive_sections: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    meeting = relationship("Meeting", back_populates="summary")

