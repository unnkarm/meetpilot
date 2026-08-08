import uuid
from app.database.session import SessionLocal
from app.models.meeting import Meeting, MeetingStatus
from app.workers.meeting_processor import process_meeting

db = SessionLocal()
try:
    queued_meetings = db.query(Meeting).filter(Meeting.status == MeetingStatus.queued).all()
    print(f"Found {len(queued_meetings)} queued meetings")
    for m in queued_meetings:
        print(f"Re-queueing meeting {m.id} - {m.title}")
        process_meeting.delay(str(m.id))
finally:
    db.close()
