from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.meeting import Meeting
from sqlalchemy import exists, select, or_
from app.schemas.notification import NotificationOut
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/notifications", response_model=list[NotificationOut])
def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id,
                or_(Notification.meeting_id.is_(None), exists(select(Meeting.id).join(
                    WorkspaceMember, WorkspaceMember.workspace_id == Meeting.workspace_id).where(
                    Meeting.id == Notification.meeting_id, WorkspaceMember.user_id == current_user.id))))
        .order_by(Notification.created_at.desc())
        .limit(30)
        .all()
    )

