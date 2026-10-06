import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_current_user, get_meeting_for_member
from app.database.session import get_db
from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.meeting import TaskOut
from app.schemas.task import TaskCreateRequest, TaskUpdateRequest
from app.services.product_events import track_event
from app.models.task import TaskStatus

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _resolve_assignee(db: Session, workspace_id: uuid.UUID, name: str | None) -> User | None:
    if not name or not name.strip():
        return None
    member = (
        db.query(User)
        .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .filter(WorkspaceMember.workspace_id == workspace_id, func.lower(User.name) == name.strip().lower())
        .first()
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Assignee must be a member of this workspace")
    return member


@router.get("", response_model=list[TaskOut])
def list_workspace_tasks(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Task]:
    membership = db.get(WorkspaceMember, (workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")

    return (
        db.query(Task)
        .join(Meeting, Meeting.id == Task.meeting_id)
        .filter(Meeting.workspace_id == workspace_id)
        .order_by(Task.created_at.desc())
        .all()
    )


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    if not payload.meeting_id and not payload.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide meeting_id or workspace_id",
        )

    target_meeting = None
    if payload.meeting_id:
        target_meeting = get_meeting_for_member(payload.meeting_id, current_user, db)
    elif payload.workspace_id:
        membership = db.get(WorkspaceMember, (payload.workspace_id, current_user.id))
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")

        target_meeting = (
            db.query(Meeting)
            .filter(Meeting.workspace_id == payload.workspace_id)
            .order_by(Meeting.created_at.desc())
            .first()
        )
        if not target_meeting:
            target_meeting = Meeting(
                workspace_id=payload.workspace_id,
                title="Action Items",
                status=MeetingStatus.completed,
                created_by=current_user.id,
            )
            db.add(target_meeting)
            db.flush()

    assignee = _resolve_assignee(db, target_meeting.workspace_id, payload.assignee_name)
    task = Task(
        meeting_id=target_meeting.id,
        title=payload.title,
        assignee_id=assignee.id if assignee else None,
        assignee_name=assignee.name if assignee else None,
        due_date=payload.due_date,
        priority=payload.priority,
        status=payload.status,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    if task.due_date:
        try:
            from app.services.google_calendar_service import sync_task_to_google_calendar
            sync_task_to_google_calendar(db, task.id)
        except Exception:
            pass

    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    membership = db.get(WorkspaceMember, (task.meeting.workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this task's workspace")

    update_data = payload.model_dump(exclude_unset=True)
    was_done = task.status == TaskStatus.done
    if any(update_data.get(field) is None for field in ("title", "priority", "status") if field in update_data):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title, priority and status cannot be null")
    if "title" in update_data and not update_data["title"].strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Task title cannot be blank")
    if "assignee_name" in update_data:
        assignee = _resolve_assignee(db, task.meeting.workspace_id, update_data["assignee_name"])
        task.assignee_id = assignee.id if assignee else None
        update_data["assignee_name"] = assignee.name if assignee else None
    for field, value in update_data.items():
        setattr(task, field, value)

    if not was_done and task.status == TaskStatus.done and not task.meeting.workspace.is_demo:
        track_event(db, "first_task_completed", current_user.id, task.meeting.workspace_id, once=True)

    db.commit()
    db.refresh(task)

    if task.due_date:
        try:
            from app.services.google_calendar_service import sync_task_to_google_calendar
            sync_task_to_google_calendar(db, task.id)
        except Exception:
            pass

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    membership = db.get(WorkspaceMember, (task.meeting.workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this task's workspace")

    db.delete(task)
    db.commit()



