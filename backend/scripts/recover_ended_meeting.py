"""Requeue one ended meeting whose analysis worker was stopped.

Run from the meeting_bot service, which mounts this scripts directory.
Requires local operator access. Does not join a call or start a browser.
"""
import argparse
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("meeting_id", type=uuid.UUID)
    parser.add_argument("--normal-end", action="store_true",
                        help="Host confirms a normal end despite a stale provider failure")
    args = parser.parse_args()

    from app.core.celery_app import celery_app
    from app.database.session import SessionLocal
    from app.models.meeting import Meeting, MeetingStatus
    from app.services.vexa_client import VexaClient
    from app.workers.vexa_meeting import finalize_capture

    # Avoid resetting a live analysis claim owned by another worker.
    active = celery_app.control.inspect(timeout=3).active() or {}
    for jobs in active.values():
        for job in jobs:
            if str(args.meeting_id) in str(job.get("args", [])):
                parser.exit(1, "This meeting still has an active worker. Wait for it to finish.\n")
    with SessionLocal() as db:
        meeting = db.get(Meeting, args.meeting_id)
        if meeting is None or meeting.source != "live":
            parser.exit(1, "Live meeting not found.\n")
        if meeting.status == MeetingStatus.completed:
            print("Meeting analysis is already complete.")
            return
        workspace_id = meeting.workspace_id
        vexa = VexaClient(workspace_id)
        binding = vexa.binding(meeting.id)  # Enforces the workspace/provider binding.
        upstream = vexa.meeting(binding["provider_id"])
        if upstream.get("status") not in {"completed", "failed"}:
            parser.exit(1, "The meeting bot is still running; recovery was not applied.\n")
        failure = None if args.normal_end or upstream.get("status") == "completed" else (
            meeting.capture_failure_reason or (upstream.get("data") or {}).get("reason")
            or "Meeting capture disconnected unexpectedly")
        # Active workers were checked above; allow an interrupted analysis claim
        # to use the ordinary queued-job claim and existing evidence pipeline.
        meeting.status = MeetingStatus.queued
        db.commit()
    if finalize_capture(args.meeting_id, workspace_id, failure):
        print("Saved meeting analysis queued. Refresh MeetPilot to follow its progress.")
    else:
        parser.exit(1, "Could not queue analysis. Check the meeting's processing error.\n")


if __name__ == "__main__":
    main()
