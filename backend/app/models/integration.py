import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class WorkspaceIntegration(Base):
    __tablename__ = "workspace_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(50), nullable=False, index=True)  # discord, google_calendar, zoom
    is_connected = Column(Boolean, default=True, nullable=False)
    encrypted_config = Column(Text, nullable=False)  # Fernet-encrypted JSON payload
    masked_identifier = Column(String(255), nullable=True)  # Safe masked URL/email for display
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    workspace = relationship("Workspace", back_populates="integrations")
