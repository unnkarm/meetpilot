"""Real SQL/HTTP review permissions, queue recovery and evidence regressions."""
import unittest
import uuid
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.api.routes import meeting_review
from app.database.base import Base
from app.models.meeting import Meeting, MeetingStatus
from app.models.meeting_review import MeetingArtifact, MeetingBookmark, SummaryTemplate
from app.models.task import Task
from app.models.transcript import TranscriptSegment, Vector
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.services.meeting_review import (
    ChaptersDraft, FollowupDraft, ReviewError, ReviewSource, SummaryDraft, fingerprint,
    generate_review, source_windows, speaking_metrics,
)
from app.workers.meeting_review import run_review


@compiles(ARRAY, "sqlite")
@compiles(JSONB, "sqlite")
@compiles(Vector, "sqlite")
def sqlite_types(element, compiler, **kwargs):
    return "TEXT"


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.sources = [ReviewSource("a", "Alice", 0, 10, "We decided to use PostgreSQL."),
                        ReviewSource("b", "Bob", 10, 20, "আমি শুক্রবার API দেখব।"),
                        ReviewSource("c", "Alice", 25, 30, "What about the migration risk?")]

    def test_summary_retains_original_speaker_quote_and_timestamp(self):
        provider = MagicMock()
        provider.structured.return_value = SummaryDraft.model_validate({"sections": [{"title": "Decisions", "points": [{"text": "Use PostgreSQL", "source_ids": ["a"]}]}]})
        result = generate_review(self.sources, "summary", {"instructions": "Executive outcomes"}, provider=provider)
        self.assertEqual(result["citations"]["a"]["quote"], self.sources[0].text)
        self.assertEqual(result["citations"]["a"]["speaker"], "Alice")
        self.assertEqual(result["citations"]["a"]["start_time"], 0)
        self.assertEqual(result["coverage"]["segments"], 3)
        self.assertNotIn("b", result["citations"])

    def test_unknown_evidence_is_rejected_in_every_format(self):
        for kind, schema, value in [
            ("summary", SummaryDraft, {"sections": [{"title": "Secret", "points": [{"text": "Foreign data", "source_ids": ["foreign"]}]}]}),
            ("followup", FollowupDraft, {"paragraphs": [{"text": "Foreign data", "source_ids": ["foreign"]}]}),
            ("chapters", ChaptersDraft, {"chapters": [{"title": "Secret", "start_segment_id": "a", "end_segment_id": "c", "points": [{"text": "Foreign data", "source_ids": ["foreign"]}]}]}),
        ]:
            with self.subTest(kind=kind):
                provider = MagicMock(); provider.structured.return_value = schema.model_validate(value)
                with self.assertRaises(ReviewError):
                    generate_review(self.sources, kind, {"instructions": "text", "format": "email", "audience": "client"}, provider=provider)

    def test_followup_respects_audience_format_language_without_sending(self):
        provider = MagicMock(); provider.structured.return_value = FollowupDraft.model_validate({"paragraphs": [{"text": "শুক্রবার API দেখা হবে।", "source_ids": ["b"]}]})
        result = generate_review(self.sources, "followup", {"format": "teams", "audience": "client", "language": "bn"}, provider=provider)
        self.assertEqual(result["format"], "teams")
        self.assertEqual(result["citations"]["b"]["quote"], "আমি শুক্রবার API দেখব।")
        self.assertIn("client", provider.structured.call_args.args[0])
        self.assertIn("bn", provider.structured.call_args.kwargs["system"])

    def test_chapters_use_real_ranges_and_cover_all_turns(self):
        provider = MagicMock(); provider.structured.return_value = ChaptersDraft.model_validate({"chapters": [
            {"title": "Database", "start_segment_id": "a", "end_segment_id": "a", "points": [{"text": "Use PostgreSQL", "source_ids": ["a"]}]},
            {"title": "Follow-up", "start_segment_id": "b", "end_segment_id": "c", "points": [{"text": "Review API", "source_ids": ["b"]}]},
        ]})
        result = generate_review(self.sources, "chapters", {}, provider=provider)
        self.assertEqual([(c["start_time"], c["end_time"]) for c in result["chapters"]], [(0, 10), (10, 30)])
        for start, end in (("b", "c"), ("a", "b"), ("c", "a")):
            provider.structured.return_value = ChaptersDraft.model_validate({"chapters": [{"title": "Invalid", "start_segment_id": start, "end_segment_id": end, "points": [{"text": "Example", "source_ids": ["a"]}]}]})
            with self.assertRaises(ReviewError):
                generate_review(self.sources, "chapters", {}, provider=provider)

    def test_context_windows_keep_every_turn_and_reject_overflow(self):
        with patch("app.services.meeting_review.WINDOW_BYTES", 250):
            windows = source_windows(self.sources)
            self.assertGreater(len(windows), 1)
            self.assertEqual([s.id for w in windows for s in w], ["a", "b", "c"])
            with patch("app.services.meeting_review.MAX_WINDOWS", 1), self.assertRaises(ReviewError):
                source_windows(self.sources)
        with self.assertRaises(ReviewError):
            source_windows([])

    def test_metrics_deduplicate_speaker_overlap_and_do_not_call_it_interruption(self):
        sources = [ReviewSource("a", "Alice", 0, 10, "um one two?"), ReviewSource("b", "Alice", 5, 15, "three four"),
                   ReviewSource("c", "Bob", 8, 12, "Why?"), ReviewSource("d", "Bob", 30, 40, "মানে ঠিক আছে")]
        result = speaking_metrics(sources, 50)
        self.assertEqual(result["speech_seconds"], 25)
        self.assertEqual(result["silence_seconds"], 25)
        self.assertEqual(result["overlap_speaker_seconds"], 4)
        self.assertEqual(result["speakers"][0]["speaking_seconds"], 15)
        self.assertEqual(result["speakers"][0]["fillers"], 1)
        self.assertAlmostEqual(sum(s["talk_share_percent"] for s in result["speakers"]), 100, delta=0.1)
        self.assertNotIn("interruptions", result)


class ReviewHTTPTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        self.db = self.factory()
        self.owner, self.member, self.other, self.outsider = [User(id=uuid.uuid4(), clerk_id="user_" + uuid.uuid4().hex,
            name=name, email=name + "@example.com") for name in ("Owner", "Alice", "Bob", "Outside")]
        self.db.add_all([self.owner, self.member, self.other, self.outsider]); self.db.flush()
        self.ws = Workspace(id=uuid.uuid4(), name="Workspace", owner_id=self.owner.id)
        self.foreign = Workspace(id=uuid.uuid4(), name="Other", owner_id=self.outsider.id)
        self.db.add_all([self.ws, self.foreign]); self.db.flush()
        for user, role in ((self.owner, WorkspaceRole.owner), (self.member, WorkspaceRole.member), (self.other, WorkspaceRole.member)):
            self.db.add(WorkspaceMember(workspace_id=self.ws.id, user_id=user.id, role=role))
        self.db.add(WorkspaceMember(workspace_id=self.foreign.id, user_id=self.outsider.id, role=WorkspaceRole.owner))
        self.meeting = Meeting(id=uuid.uuid4(), workspace_id=self.ws.id, title="Planning", created_by=self.owner.id, duration_seconds=60, status=MeetingStatus.completed)
        self.foreign_meeting = Meeting(id=uuid.uuid4(), workspace_id=self.foreign.id, title="Other", created_by=self.outsider.id, status=MeetingStatus.completed)
        self.db.add_all([self.meeting, self.foreign_meeting]); self.db.flush()
        self.segment = TranscriptSegment(id=uuid.uuid4(), meeting_id=self.meeting.id, speaker="Alice", start_time=10, end_time=20, text="We decided to use PostgreSQL.")
        self.db.add(self.segment); self.db.commit()
        self.actor = self.member
        self.app = FastAPI(); self.app.include_router(meeting_review.router)
        self.app.dependency_overrides[get_current_user] = lambda: self.actor
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(self.app)
        self.root = f"/api/v1/meetings/{self.meeting.id}"
        self.queue = patch("app.workers.meeting_review.generate_meeting_review.delay").start()

    def tearDown(self):
        patch.stopall(); self.client.close(); self.db.close(); self.engine.dispose()

    def create_draft(self, **kwargs):
        response = self.client.post(self.root + "/review/artifacts", json={"kind": "summary", **kwargs})
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()["id"]

    def test_live_meeting_responses_keep_workspace_for_review_tools(self):
        from app.api.routes import live_meetings
        self.app.include_router(live_meetings.router)
        with patch.object(live_meetings.VexaClient, "preflight"), \
                patch.object(live_meetings.run_vexa_meeting_bot_task, "apply_async"), \
                patch.object(live_meetings.process_live_meeting, "apply_async"):
            response = self.client.post("/api/v1/meetings/live/start", json={
                "workspace_id": str(self.ws.id), "meeting_url": "https://meet.google.com/abc-defg-hij"})
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["workspace_id"], str(self.ws.id))
            response = self.client.post(f"/api/v1/meetings/live/{response.json()['id']}/stop")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["workspace_id"], str(self.ws.id))

    def test_templates_are_shared_and_only_managers_can_mutate(self):
        endpoint = f"/api/v1/workspaces/{self.ws.id}/summary-templates"
        self.assertEqual(len(self.client.get(endpoint).json()["templates"]), 5)
        payload = {"name": "Custom", "instructions": "Focus on launch blockers"}
        self.assertEqual(self.client.post(endpoint, json=payload).status_code, 403)
        self.actor = self.owner
        response = self.client.post(endpoint, json=payload); self.assertEqual(response.status_code, 201)
        ident = response.json()["id"]
        self.assertEqual(self.client.patch(endpoint + "/" + ident, json={**payload, "name": "Updated"}).status_code, 200)
        self.actor = self.member
        self.assertFalse(self.client.get(endpoint).json()["can_manage"])
        self.assertEqual(self.client.delete(endpoint + "/" + ident).status_code, 403)

    def test_foreign_template_and_meeting_are_never_used(self):
        template = SummaryTemplate(id=uuid.uuid4(), workspace_id=self.foreign.id, created_by=self.outsider.id, name="Private", instructions="Private instructions")
        self.db.add(template); self.db.commit()
        response = self.client.post(self.root + "/review/artifacts", json={"kind": "summary", "template_id": str(template.id)})
        self.assertEqual(response.status_code, 404)
        foreign = f"/api/v1/meetings/{self.foreign_meeting.id}"
        for suffix in ("/review/artifacts", "/review/metrics", "/review/risks", "/bookmarks"):
            self.assertEqual(self.client.get(foreign + suffix).status_code, 403)
        self.queue.assert_not_called()

    def test_queue_submission_is_idempotent_and_drafts_are_personal(self):
        ident = str(uuid.uuid4())
        self.create_draft(id=ident); self.create_draft(id=ident)
        self.queue.assert_called_once()
        self.actor = self.other
        self.assertEqual(self.client.get(self.root + "/review/artifacts").json(), [])
        self.assertEqual(self.client.get(self.root + f"/review/artifacts/{ident}").status_code, 404)
        self.assertEqual(self.client.delete(self.root + f"/review/artifacts/{ident}").status_code, 404)
        self.assertEqual(self.client.post(self.root + "/review/artifacts", json={"kind": "summary", "id": ident}).status_code, 404)

    def test_pending_limit_retry_guard_and_cancellation(self):
        ids = [self.create_draft() for _ in range(3)]
        self.assertEqual(self.client.post(self.root + "/review/artifacts", json={"kind": "summary"}).status_code, 409)
        self.assertEqual(self.client.post(self.root + f"/review/artifacts/{ids[0]}/retry").status_code, 409)
        self.assertEqual(self.client.delete(self.root + f"/review/artifacts/{ids[0]}").status_code, 204)
        self.create_draft()

    def test_queue_failure_is_visible_and_retryable(self):
        self.queue.side_effect = RuntimeError("broker offline")
        ident = self.create_draft()
        response = self.client.get(self.root + f"/review/artifacts/{ident}").json()
        self.assertEqual(response["status"], "failed")
        self.assertIn("worker is unavailable", response["failure_reason"])
        self.queue.side_effect = None
        self.assertEqual(self.client.post(self.root + f"/review/artifacts/{ident}/retry").status_code, 202)

    def test_stale_processing_retry_invalidates_old_lease(self):
        ident = self.create_draft()
        row = self.db.get(MeetingArtifact, uuid.UUID(ident))
        row.status, row.run_token = "processing", "old-worker-token"
        row.updated_at = datetime.now(timezone.utc) - timedelta(minutes=21)
        self.db.commit()
        response = self.client.post(self.root + f"/review/artifacts/{ident}/retry")
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["status"], "queued")
        self.db.refresh(row)
        self.assertIsNone(row.run_token)

    def test_bookmark_bounds_idempotency_and_delete_permissions(self):
        ident = str(uuid.uuid4())
        payload = {"id": ident, "kind": "decision", "label": "Database", "position_seconds": 15}
        for _ in range(2):
            self.assertEqual(self.client.post(self.root + "/bookmarks", json=payload).status_code, 201)
        rows = self.client.get(self.root + "/bookmarks").json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_segment_id"], str(self.segment.id))
        self.assertEqual(self.client.post(self.root + "/bookmarks", json={**payload, "id": str(uuid.uuid4()), "position_seconds": 61}).status_code, 422)
        self.actor = self.other
        self.assertFalse(self.client.get(self.root + "/bookmarks").json()[0]["can_delete"])
        self.assertEqual(self.client.delete(self.root + f"/bookmarks/{ident}").status_code, 403)
        self.actor = self.owner
        self.assertEqual(self.client.delete(self.root + f"/bookmarks/{ident}").status_code, 204)

    def test_removed_member_cannot_read_drafts_or_bookmarks(self):
        ident = self.create_draft()
        self.db.delete(self.db.get(WorkspaceMember, (self.ws.id, self.member.id))); self.db.commit()
        for path in (f"/review/artifacts/{ident}", "/bookmarks", "/review/metrics", "/review/risks"):
            self.assertEqual(self.client.get(self.root + path).status_code, 403)

    def test_risk_review_filters_tasks_before_display(self):
        tasks = [Task(meeting_id=self.meeting.id, title="Mine", assignee_id=self.member.id),
                 Task(meeting_id=self.meeting.id, title="Other person's task", assignee_id=self.other.id),
                 Task(meeting_id=self.meeting.id, title="Unverified", assignee_name="Alice")]
        self.db.add_all(tasks); self.db.commit()
        self.assertEqual([r["title"] for r in self.client.get(self.root + "/review/risks").json()["risks"]], ["Mine"])
        self.actor = self.owner
        rows = self.client.get(self.root + "/review/risks").json()["risks"]
        self.assertEqual(len(rows), 3)
        self.assertIn("Owner is not verified", next(r for r in rows if r["title"] == "Unverified")["reasons"])

    def provider(self):
        provider = MagicMock()
        provider.structured.return_value = SummaryDraft.model_validate({"sections": [{"title": "Decisions", "points": [{"text": "Use PostgreSQL", "source_ids": [str(self.segment.id)]}]}]})
        return provider

    def test_worker_persists_grounded_draft_and_duplicate_delivery_does_not_reinfer(self):
        ident = self.create_draft(); provider = self.provider()
        with patch("app.services.meeting_review.get_ai_provider", return_value=provider):
            run_review(ident, self.factory); run_review(ident, self.factory)
        self.db.expire_all()
        row = self.db.get(MeetingArtifact, uuid.UUID(ident))
        self.assertEqual(row.status, "completed")
        self.assertEqual(row.payload["citations"][str(self.segment.id)]["quote"], self.segment.text)
        provider.structured.assert_called_once()

    def test_worker_revocation_and_changed_source_stop_generation(self):
        ident = self.create_draft()
        self.segment.text = "Corrected source"; self.db.commit()
        with patch("app.services.meeting_review.get_ai_provider") as provider:
            run_review(ident, self.factory)
            provider.assert_not_called()
        self.db.expire_all()
        self.assertEqual(self.db.get(MeetingArtifact, uuid.UUID(ident)).status, "failed")
        ident2 = self.create_draft()
        self.db.delete(self.db.get(WorkspaceMember, (self.ws.id, self.member.id))); self.db.commit()
        with patch("app.services.meeting_review.get_ai_provider") as provider:
            run_review(ident2, self.factory)
            provider.assert_not_called()

    def test_transcript_change_marks_existing_result_stale(self):
        ident = self.create_draft()
        with patch("app.services.meeting_review.get_ai_provider", return_value=self.provider()):
            run_review(ident, self.factory)
        self.db.expire_all(); self.segment.text = "Changed after generation"; self.db.commit()
        self.assertTrue(self.client.get(self.root + f"/review/artifacts/{ident}").json()["stale"])

    def test_stale_worker_cannot_overwrite_new_lease(self):
        ident = self.create_draft(); provider = self.provider()
        output = provider.structured.return_value
        def supersede(*args, **kwargs):
            with self.factory() as db:
                row = db.get(MeetingArtifact, uuid.UUID(ident)); row.run_token = "new-run-token"; row.status = "completed"; row.payload = {"new": True}; db.commit()
            return output
        provider.structured.side_effect = supersede
        with patch("app.services.meeting_review.get_ai_provider", return_value=provider):
            run_review(ident, self.factory)
        self.db.expire_all()
        self.assertEqual(self.db.get(MeetingArtifact, uuid.UUID(ident)).payload, {"new": True})

    def test_worker_checks_revocation_again_after_inference(self):
        ident = self.create_draft(); provider = self.provider(); output = provider.structured.return_value
        def revoke(*args, **kwargs):
            with self.factory() as db:
                db.delete(db.get(WorkspaceMember, (self.ws.id, self.member.id))); db.commit()
            return output
        provider.structured.side_effect = revoke
        with patch("app.services.meeting_review.get_ai_provider", return_value=provider):
            run_review(ident, self.factory)
        self.db.expire_all()
        row = self.db.get(MeetingArtifact, uuid.UUID(ident))
        self.assertEqual(row.status, "failed")
        self.assertIsNone(row.payload)

    def test_new_migration_handles_existing_schema_and_bootstrap(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        from sqlalchemy import inspect
        path = Path(__file__).parents[1] / "alembic/versions/f6a7b8c9d0e1_meeting_review.py"
        spec = importlib.util.spec_from_file_location("review_migration", path)
        migration = importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
        tables = ("meeting_bookmarks", "meeting_artifacts", "summary_templates")
        with self.engine.begin() as conn:
            for table in tables:
                Base.metadata.tables[table].drop(conn)
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
                migration.upgrade()  # Same case as bootstrap preceding Alembic.
            inspector = inspect(conn)
            for table in tables:
                self.assertEqual({c["name"] for c in inspector.get_columns(table)}, set(Base.metadata.tables[table].columns.keys()))
                self.assertTrue(inspector.get_indexes(table))
            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()
            self.assertIn("meetings", inspect(conn).get_table_names())


if __name__ == "__main__":
    unittest.main()
