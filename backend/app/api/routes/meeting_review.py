"""Authenticated review tools. Drafts are personal; bookmarks are workspace-visible."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_meeting_for_member
from app.database.session import get_db
from app.models.meeting import Meeting, MeetingSummary
from app.models.meeting_review import MeetingArtifact, MeetingBookmark, SummaryTemplate
from app.models.task import Task, TaskStatus
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.access_control import is_manager, lock_workspace_manager, membership_for, require_manager, task_visibility
from app.services.meeting_review import BUILTIN_TEMPLATES, ReviewError, fingerprint, sources_for_rows, source_windows, speaking_metrics

router = APIRouter(prefix="/api/v1", tags=["review"])


def transcript_rows(db, meeting_id):
    return db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.start_time, TranscriptSegment.id).all()


class TemplateInput(BaseModel):
    name: str = Field(min_length=3, max_length=80, pattern=r"\S")
    instructions: str = Field(min_length=10, max_length=2000, pattern=r"\S")


@router.get("/workspaces/{workspace_id}/summary-templates")
def list_templates(workspace_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member = membership_for(db, workspace_id, user.id)
    rows = db.query(SummaryTemplate).filter(SummaryTemplate.workspace_id == workspace_id).order_by(SummaryTemplate.created_at).all()
    return {"can_manage": is_manager(member), "templates": [
        {"id": key, **value, "builtin": True} for key, value in BUILTIN_TEMPLATES.items()
    ] + [{"id": str(row.id), "name": row.name, "instructions": row.instructions, "builtin": False} for row in rows]}


@router.post("/workspaces/{workspace_id}/summary-templates", status_code=201)
def create_template(workspace_id: uuid.UUID, payload: TemplateInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lock_workspace_manager(db, workspace_id, user.id)
    if db.query(SummaryTemplate).filter(SummaryTemplate.workspace_id == workspace_id).count() >= 50:
        raise HTTPException(409, "This workspace has reached the 50-template limit")
    row = SummaryTemplate(workspace_id=workspace_id, created_by=user.id, name=payload.name.strip(), instructions=payload.instructions.strip())
    db.add(row); db.commit(); db.refresh(row)
    return {"id": str(row.id), "name": row.name, "instructions": row.instructions, "builtin": False}


def workspace_template(db, workspace_id, template_id):
    row = db.get(SummaryTemplate, template_id)
    if row is None or row.workspace_id != workspace_id:
        raise HTTPException(404, "Template not found in this workspace")
    return row


@router.patch("/workspaces/{workspace_id}/summary-templates/{template_id}")
def update_template(workspace_id: uuid.UUID, template_id: uuid.UUID, payload: TemplateInput,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lock_workspace_manager(db, workspace_id, user.id)
    row = workspace_template(db, workspace_id, template_id)
    row.name, row.instructions = payload.name.strip(), payload.instructions.strip()
    db.commit()
    return {"id": str(row.id), "name": row.name, "instructions": row.instructions, "builtin": False}


@router.delete("/workspaces/{workspace_id}/summary-templates/{template_id}", status_code=204)
def delete_template(workspace_id: uuid.UUID, template_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lock_workspace_manager(db, workspace_id, user.id)
    db.delete(workspace_template(db, workspace_id, template_id)); db.commit()


class ArtifactRequest(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    kind: Literal["summary", "followup", "chapters"]
    template_id: str = Field(default="executive", max_length=36)
    format: Literal["email", "slack", "teams"] = "email"
    audience: Literal["internal", "client"] = "internal"
    language: Literal["meeting", "en", "bn", "hi"] = "meeting"


def own_artifact(db, meeting, user, artifact_id, *, lock=False):
    query = db.query(MeetingArtifact).filter(MeetingArtifact.id == artifact_id,
        MeetingArtifact.meeting_id == meeting.id, MeetingArtifact.workspace_id == meeting.workspace_id,
        MeetingArtifact.created_by == user.id)
    row = (query.with_for_update() if lock else query).first()
    if row is None:
        raise HTTPException(404, "Draft not found")
    return row


def artifact_out(row, *, detail=False, stale=False):
    result = {"id": str(row.id), "kind": row.kind, "status": row.status,
              "options": row.options, "failure_reason": row.failure_reason, "created_at": row.created_at,
              "ai_model": row.ai_model, "progress": (row.payload or {}).get("progress")}
    if detail:
        result.update(payload=row.payload, stale=stale)
    return result


def dispatch(db, row):
    from app.workers.meeting_review import generate_meeting_review
    try:
        generate_meeting_review.delay(str(row.id))
    except Exception:
        row.status = "failed"
        row.failure_reason = "Review worker is unavailable. Start the processing worker and retry this draft."
        db.commit()


def lock_pending_limit(db, workspace_id, user_id, exclude=None):
    # Serialize submissions by this approved member before checking the cap.
    member = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id).with_for_update().populate_existing().first()
    if member is None:
        raise HTTPException(403, "Not a member of this workspace")
    query = db.query(MeetingArtifact).filter(MeetingArtifact.workspace_id == workspace_id,
        MeetingArtifact.created_by == user_id, MeetingArtifact.status.in_(["queued", "processing"]))
    if exclude:
        query = query.filter(MeetingArtifact.id != exclude)
    if query.count() >= 3:
        raise HTTPException(409, "You already have three pending review drafts. Finish or cancel them first.")


@router.post("/meetings/{meeting_id}/review/artifacts", status_code=202)
def create_artifact(meeting_id: uuid.UUID, payload: ArtifactRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    existing = db.get(MeetingArtifact, payload.id)
    if existing is not None:
        return artifact_out(own_artifact(db, meeting, user, payload.id))
    sources = sources_for_rows(transcript_rows(db, meeting.id))
    try:
        source_windows(sources)
    except ReviewError as exc:
        raise HTTPException(422, str(exc)) from None
    lock_pending_limit(db, meeting.workspace_id, user.id)
    options = payload.model_dump(mode="json", exclude={"id", "kind"})
    if payload.kind == "summary":
        template = BUILTIN_TEMPLATES.get(payload.template_id)
        if template is None:
            try:
                template = workspace_template(db, meeting.workspace_id, uuid.UUID(payload.template_id))
            except ValueError:
                raise HTTPException(422, "Unknown summary template") from None
            options.update(template_name=template.name, instructions=template.instructions)
        else:
            options.update(template_name=template["name"], instructions=template["instructions"])
    row = MeetingArtifact(id=payload.id, meeting_id=meeting.id, workspace_id=meeting.workspace_id,
                          created_by=user.id, kind=payload.kind, options=options, source_fingerprint=fingerprint(sources))
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return artifact_out(own_artifact(db, meeting, user, payload.id))
    dispatch(db, row)
    return artifact_out(row)


@router.get("/meetings/{meeting_id}/review/artifacts")
def list_artifacts(meeting_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    rows = db.query(MeetingArtifact).filter(MeetingArtifact.meeting_id == meeting.id,
        MeetingArtifact.workspace_id == meeting.workspace_id, MeetingArtifact.created_by == user.id).order_by(MeetingArtifact.created_at.desc(), MeetingArtifact.id).limit(30).all()
    return [artifact_out(row) for row in rows]


@router.get("/meetings/{meeting_id}/review/artifacts/{artifact_id}")
def get_artifact(meeting_id: uuid.UUID, artifact_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    row = own_artifact(db, meeting, user, artifact_id)
    current = fingerprint(sources_for_rows(transcript_rows(db, meeting.id)))
    return artifact_out(row, detail=True, stale=current != row.source_fingerprint)


@router.post("/meetings/{meeting_id}/review/artifacts/{artifact_id}/retry", status_code=202)
def retry_artifact(meeting_id: uuid.UUID, artifact_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    lock_pending_limit(db, meeting.workspace_id, user.id, exclude=artifact_id)
    row = own_artifact(db, meeting, user, artifact_id, lock=True)
    updated = row.updated_at.replace(tzinfo=timezone.utc) if row.updated_at.tzinfo is None else row.updated_at
    if row.status in {"queued", "processing"} and updated > datetime.now(timezone.utc) - timedelta(minutes=20):
        raise HTTPException(409, "This draft is still running; retry after it fails or becomes stale")
    sources = sources_for_rows(transcript_rows(db, meeting.id))
    try:
        source_windows(sources)
    except ReviewError as exc:
        raise HTTPException(422, str(exc)) from None
    row.status, row.run_token, row.failure_reason, row.payload = "queued", None, None, None
    row.source_fingerprint, row.updated_at = fingerprint(sources), datetime.now(timezone.utc)
    db.commit(); dispatch(db, row)
    return artifact_out(row)


@router.delete("/meetings/{meeting_id}/review/artifacts/{artifact_id}", status_code=204)
def delete_artifact(meeting_id: uuid.UUID, artifact_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    db.delete(own_artifact(db, meeting, user, artifact_id, lock=True)); db.commit()


class BookmarkRequest(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    kind: Literal["decision", "followup", "highlight"] = "highlight"
    label: str = Field(default="Highlight", min_length=1, max_length=160, pattern=r"\S")
    position_seconds: float = Field(ge=0, le=86400, allow_inf_nan=False)


def bookmark_out(row, user_id, manager):
    return {"id": str(row.id), "kind": row.kind, "label": row.label, "position_seconds": row.position_seconds,
            "source_segment_id": str(row.source_segment_id) if row.source_segment_id else None,
            "can_delete": row.created_by == user_id or manager}


@router.get("/meetings/{meeting_id}/bookmarks")
def list_bookmarks(meeting_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    manager = is_manager(membership_for(db, meeting.workspace_id, user.id))
    rows = db.query(MeetingBookmark).filter(MeetingBookmark.meeting_id == meeting.id).order_by(MeetingBookmark.position_seconds, MeetingBookmark.id).limit(500).all()
    return [bookmark_out(row, user.id, manager) for row in rows]


@router.post("/meetings/{meeting_id}/bookmarks", status_code=201)
def create_bookmark(meeting_id: uuid.UUID, payload: BookmarkRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    db.query(Meeting).filter(Meeting.id == meeting.id).with_for_update().first()
    manager = is_manager(membership_for(db, meeting.workspace_id, user.id))
    existing = db.get(MeetingBookmark, payload.id)
    if existing:
        if existing.meeting_id != meeting.id or existing.created_by != user.id:
            raise HTTPException(404, "Bookmark not found")
        return bookmark_out(existing, user.id, manager)
    rows = transcript_rows(db, meeting.id)
    if not rows:
        raise HTTPException(422, "Wait for the first saved speech turn before bookmarking")
    limit = max(float(meeting.duration_seconds or 0), max(row.end_time for row in rows))
    if payload.position_seconds > limit:
        raise HTTPException(422, "Bookmark time must fall within the captured meeting")
    if db.query(MeetingBookmark).filter(MeetingBookmark.meeting_id == meeting.id).count() >= 500:
        raise HTTPException(409, "This meeting has reached the 500-bookmark limit")
    closest = min(rows, key=lambda row: (0 if row.start_time <= payload.position_seconds <= row.end_time
                                       else min(abs(row.start_time - payload.position_seconds), abs(row.end_time - payload.position_seconds))))
    row = MeetingBookmark(id=payload.id, meeting_id=meeting.id, created_by=user.id, kind=payload.kind,
                          label=payload.label.strip(), position_seconds=payload.position_seconds, source_segment_id=closest.id)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        row = db.get(MeetingBookmark, payload.id)
        if row is None or row.meeting_id != meeting.id or row.created_by != user.id:
            raise HTTPException(404, "Bookmark not found") from None
    return bookmark_out(row, user.id, manager)


@router.delete("/meetings/{meeting_id}/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(meeting_id: uuid.UUID, bookmark_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    row = db.get(MeetingBookmark, bookmark_id)
    if row is None or row.meeting_id != meeting.id:
        raise HTTPException(404, "Bookmark not found")
    if row.created_by != user.id:
        require_manager(db, meeting.workspace_id, user.id)
    db.delete(row); db.commit()


@router.get("/meetings/{meeting_id}/review/metrics")
def review_metrics(meeting_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    return speaking_metrics(sources_for_rows(transcript_rows(db, meeting.id)), meeting.duration_seconds)


@router.get("/meetings/{meeting_id}/review/risks")
def review_risks(meeting_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_for_member(meeting_id, user, db)
    tasks = db.query(Task).join(Meeting, Meeting.id == Task.meeting_id).filter(
        Task.meeting_id == meeting.id, task_visibility(user.id), Task.status != TaskStatus.done).all()
    risks = []
    for task in tasks:
        reasons = []
        if task.assignee_id is None:
            reasons.append("Owner is not verified")
        if not task.due_date:
            reasons.append("No deadline recorded")
        if reasons:
            risks.append({"id": "task:" + str(task.id), "kind": "task", "title": task.title, "reasons": reasons,
                          "source_segment_id": str(task.source_segment_id) if task.source_segment_id else None,
                          "quote": task.source_quote, "speaker": task.source_speaker, "timestamp": task.transcript_timestamp})
    summary = db.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting.id).first()
    sources = {s.id: s for s in sources_for_rows(transcript_rows(db, meeting.id))}
    for index, point in enumerate((summary.executive_sections or {}).get("blockers", []) if summary else []):
        if not isinstance(point, dict):
            continue
        source = sources.get(str(point.get("source_segment_id")))
        quote = point.get("source_quote")
        if source and isinstance(quote, str) and quote.strip() and quote in source.text:
            risks.append({"id": f"blocker:{index}", "kind": "blocker", "title": point.get("text", quote),
                          "reasons": ["Mentioned blocker — review current status"], "source_segment_id": source.id,
                          "quote": quote, "speaker": source.speaker, "position_seconds": source.start})
    return {"risks": risks, "note": "Missing metadata and mentioned blockers need review; they do not prove a missed commitment."}
