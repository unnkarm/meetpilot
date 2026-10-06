"""Deterministic sample workspace; never inserted into a customer's real workspace."""

import uuid

from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.models.document import DocumentChunk, KnowledgeDocument
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus, MeetingSummary
from app.models.task import Task, TaskPriority
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


def create_demo_workspace(db: Session, user: User) -> Workspace:
    existing = db.query(Workspace).filter(Workspace.owner_id == user.id, Workspace.is_demo.is_(True)).first()
    if existing:
        return existing

    workspace = Workspace(id=uuid.uuid4(), name="MeetPilot Demo · Sample Data", owner_id=user.id, is_demo=True)
    db.add(workspace)
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.owner))
    db.flush()

    meetings = [
        (
            "Sample · Product Planning",
            [
                (12.0, 20.0, "Maya", "The customer onboarding flow should show a first meeting upload before advanced analytics."),
                (24.0, 33.0, "Noah", "I agree. We will ship the upload-first onboarding flow in the next release."),
                (40.0, 49.0, "Maya", "Noah, please prepare the upload screen by Friday so we can test it."),
            ],
            "The team agreed to prioritize an upload-first onboarding flow for new customers.",
            "Onboarding approach", "Ship an upload-first onboarding flow in the next release.",
            "Prepare the upload screen",
        ),
        (
            "Sample · Authentication Review",
            [
                (8.0, 17.0, "Leah", "Our current authentication uses Clerk for sign-in and workspace membership on the API."),
                (22.0, 31.0, "Maya", "We decided to keep Clerk and enforce workspace checks on every meeting and document request."),
                (36.0, 44.0, "Leah", "I will review the document endpoint permissions before the beta."),
            ],
            "The team kept Clerk for sign-in and agreed to audit server-side workspace authorization.",
            "Authentication architecture", "Keep Clerk and enforce server-side workspace checks.",
            "Review document endpoint permissions",
        ),
    ]

    for title, turns, overview, topic, outcome, task_title in meetings:
        meeting = Meeting(id=uuid.uuid4(), workspace_id=workspace.id, title=title,
                          source="demo", status=MeetingStatus.completed, created_by=user.id,
                          duration_seconds=int(turns[-1][1]))
        db.add(meeting)
        db.flush()
        segments = []
        for start, end, speaker, text in turns:
            segment = TranscriptSegment(id=uuid.uuid4(), meeting_id=meeting.id, speaker=speaker,
                                        start_time=start, end_time=end, text=text)
            segments.append(segment)
            db.add(segment)
        db.flush()
        for speaker in sorted({turn[2] for turn in turns}):
            db.add(MeetingParticipant(meeting_id=meeting.id, name=speaker, role="Sample participant"))
        db.add(MeetingSummary(meeting_id=meeting.id, overview=overview,
                              key_takeaways=[outcome], next_steps=[task_title],
                              ai_model="sample", prompt_version="demo-v1"))
        db.add(Decision(meeting_id=meeting.id, topic=topic, outcome=outcome,
                        transcript_timestamp=f"00:{int(turns[1][0]):02d}",
                        source_segment_id=segments[1].id, ai_model="sample", prompt_version="demo-v1"))
        db.add(Task(meeting_id=meeting.id, title=task_title, assignee_name=None,
                    priority=TaskPriority.medium, transcript_timestamp=f"00:{int(turns[2][0]):02d}",
                    source_segment_id=segments[2].id, ai_model="sample", prompt_version="demo-v1"))

    document = KnowledgeDocument(id=uuid.uuid4(), workspace_id=workspace.id,
                                 title="Sample Product Brief", filename="sample-product-brief.md",
                                 file_type="md", file_size=190, status="ready", chunk_count=1,
                                 created_by=user.id)
    db.add(document)
    db.add(DocumentChunk(id=uuid.uuid4(), document_id=document.id, workspace_id=workspace.id,
                         chunk_index=0, page_number=1,
                         text=("Sample product brief: MeetPilot helps teams turn meeting transcripts into "
                               "evidence-linked summaries, tasks and decisions. The beta prioritizes "
                               "upload-first onboarding and Clerk workspace authorization.")))
    db.commit()
    db.refresh(workspace)
    return workspace
