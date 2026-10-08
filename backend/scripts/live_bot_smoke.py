"""Operator CLI to dispatch through the same membership-checked live route."""
import argparse
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api.routes.live_meetings import start_live_meeting
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.meeting import LiveMeetingStartRequest


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-id", required=True, type=uuid.UUID)
    parser.add_argument("--user-id", required=True, type=uuid.UUID)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.get(User, args.user_id)
        if user is None:
            raise RuntimeError("Workspace user does not exist")
        result = await start_live_meeting(LiveMeetingStartRequest(
            workspace_id=args.workspace_id, meeting_url=args.url,
            title="Vexa bot join verification"), current_user=user, db=db)
        print(f"meeting_id={result.id} status={result.status}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
