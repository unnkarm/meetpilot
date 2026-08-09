import uuid
from datetime import datetime

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy.types import UserDefinedType

    class Vector(UserDefinedType):  # type: ignore[no-redef]
        def __init__(self, dim=None):
            self.dim = dim

        def get_col_spec(self, **kw):
            return f"vector({self.dim})" if self.dim else "vector"

        class comparator_factory(UserDefinedType.Comparator):
            def cosine_distance(self, other):
                return self.op("<=>")(other)
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

# text-embedding-004 produces 768-dimensional vectors.
EMBEDDING_DIM = 768


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    speaker: Mapped[str] = mapped_column(String(255), nullable=False)

    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    meeting = relationship("Meeting", back_populates="transcript_segments")
