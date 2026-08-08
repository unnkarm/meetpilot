import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    message: str
    meeting_id: uuid.UUID | None = None
    read: bool = False
    created_at: datetime
