"""Rollback-only check of Pilot intent routing against local PostgreSQL and Qwen."""

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.session import engine
from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.pilot_observability import PilotTrace
from app.services.pilot_runtime import execute_pilot_query


def main() -> None:
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)
    try:
        marker = uuid.uuid4().hex
        host = User(id=uuid.uuid4(), clerk_id="offline-host-" + marker,
                    name="Offline Host", email=f"host-{marker}@example.test")
        john = User(id=uuid.uuid4(), clerk_id="offline-john-" + marker,
                    name="John", email=f"john-{marker}@example.test")
        outsider = User(id=uuid.uuid4(), clerk_id="offline-out-" + marker,
                        name="Outsider", email=f"out-{marker}@example.test")
        db.add_all([host, john, outsider])
        db.flush()
        workspace = Workspace(id=uuid.uuid4(), name="Offline Pilot smoke", owner_id=host.id)
        db.add(workspace)
        db.flush()
        db.add_all([
            WorkspaceMember(workspace_id=workspace.id, user_id=host.id),
            WorkspaceMember(workspace_id=workspace.id, user_id=john.id),
        ])
        live = Meeting(id=uuid.uuid4(), workspace_id=workspace.id, title="Migration review",
                       created_by=host.id, status=MeetingStatus.in_progress, source="live")
        past = Meeting(id=uuid.uuid4(), workspace_id=workspace.id, title="Budget review",
                       created_by=host.id, status=MeetingStatus.completed, source="upload")
        db.add_all([live, past])
        db.flush()
        db.add_all([
            TranscriptSegment(meeting_id=live.id, speaker="John", start_time=12,
                              end_time=17, text="We decided to complete the database migration on Friday."),
            TranscriptSegment(meeting_id=past.id, speaker="Offline Host", start_time=32,
                              end_time=36, text="Our budget agreement was twelve thousand dollars."),
        ])
        db.flush()
        trace = PilotTrace(live.id, workspace.id)

        live_answer = execute_pilot_query(
            db, live.id, workspace.id, host,
            "What did we just decide about the database migration?", "Hey Pilot", trace,
        )
        assert live_answer["citations"], live_answer
        assert any(cite.get("timestamp") == "00:12" for cite in live_answer["citations"]), live_answer
        print(f"live_context=ok citations={len(live_answer['citations'])}")

        historical = execute_pilot_query(
            db, live.id, workspace.id, host,
            "What was our budget agreement in last week's meeting?", "Hey Pilot", trace,
        )
        assert historical["citations"], historical
        assert any(cite.get("meeting_id") == str(past.id) for cite in historical["citations"]), historical
        print(f"workspace_rag=ok citations={len(historical['citations'])}")

        task_result = execute_pilot_query(
            db, live.id, workspace.id, host,
            "Create a task for John to review the PR by Friday", "Hey Pilot", trace,
        )
        task = db.get(Task, uuid.UUID(task_result["task_id"]))
        assert task and task.assignee_id == john.id and task.source_quote and task.due_date
        print("verified_task=ok")

        try:
            execute_pilot_query(db, live.id, workspace.id, outsider,
                                "What did we decide?", "Hey Pilot", trace)
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("Outsider accessed live meeting context")
        print("outsider_denial=ok")
    finally:
        db.close()
        transaction.rollback()
        connection.close()


if __name__ == "__main__":
    main()
