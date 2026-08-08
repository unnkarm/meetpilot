import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_user_workspace_ids
from app.database.session import get_db
from app.models.decision import Decision
from app.models.meeting import Meeting
from app.models.task import Task
from app.models.transcript import TranscriptSegment
from app.models.user import User

router = APIRouter(prefix="/api/v1/search", tags=["search"])

MAX_RESULTS_PER_CATEGORY = 10


class SearchResult(BaseModel):
    type: str  # "meeting" | "transcript" | "task" | "decision"
    meeting_id: uuid.UUID
    meeting_title: str
    snippet: str
    timestamp: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    workspace_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    user_ws_ids = get_user_workspace_ids(current_user, db)
    if workspace_id:
        if workspace_id not in user_ws_ids:
            return SearchResponse(query=q, results=[])
        workspace_ids = [workspace_id]
    else:
        workspace_ids = user_ws_ids

    if not workspace_ids:
        return SearchResponse(query=q, results=[])


    like_pattern = f"%{q}%"
    results: list[SearchResult] = []

    # Meeting titles
    meetings = (
        db.query(Meeting)
        .filter(Meeting.workspace_id.in_(workspace_ids), Meeting.title.ilike(like_pattern))
        .limit(MAX_RESULTS_PER_CATEGORY)
        .all()
    )
    for m in meetings:
        results.append(SearchResult(type="meeting", meeting_id=m.id, meeting_title=m.title, snippet=m.title))

    # Transcript text
    segment_rows = (
        db.query(TranscriptSegment, Meeting.title)
        .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
        .filter(Meeting.workspace_id.in_(workspace_ids), TranscriptSegment.text.ilike(like_pattern))
        .limit(MAX_RESULTS_PER_CATEGORY)
        .all()
    )
    for seg, meeting_title in segment_rows:
        results.append(
            SearchResult(
                type="transcript",
                meeting_id=seg.meeting_id,
                meeting_title=meeting_title,
                snippet=seg.text,
                timestamp=f"{int(seg.start_time // 60):02d}:{int(seg.start_time % 60):02d}",
            )
        )

    # Tasks
    task_rows = (
        db.query(Task, Meeting.title)
        .join(Meeting, Meeting.id == Task.meeting_id)
        .filter(Meeting.workspace_id.in_(workspace_ids), Task.title.ilike(like_pattern))
        .limit(MAX_RESULTS_PER_CATEGORY)
        .all()
    )
    for task, meeting_title in task_rows:
        results.append(
            SearchResult(
                type="task",
                meeting_id=task.meeting_id,
                meeting_title=meeting_title,
                snippet=task.title,
                timestamp=task.transcript_timestamp,
            )
        )

    # Decisions
    decision_rows = (
        db.query(Decision, Meeting.title)
        .join(Meeting, Meeting.id == Decision.meeting_id)
        .filter(
            Meeting.workspace_id.in_(workspace_ids),
            (Decision.topic.ilike(like_pattern)) | (Decision.outcome.ilike(like_pattern)),
        )
        .limit(MAX_RESULTS_PER_CATEGORY)
        .all()
    )
    for decision, meeting_title in decision_rows:
        results.append(
            SearchResult(
                type="decision",
                meeting_id=decision.meeting_id,
                meeting_title=meeting_title,
                snippet=f"{decision.topic}: {decision.outcome}",
                timestamp=decision.transcript_timestamp,
            )
        )

    return SearchResponse(query=q, results=results)
