"""Real SQL + HTTP permission regressions; no Docker, STT, or LLM startup."""
import io
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.transcript import Vector, TranscriptSegment
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole, WorkspaceJoinRequest
from app.models.meeting import Meeting, MeetingParticipant, MeetingStatus
from app.models.task import Task, TaskStatus
from app.models.document import KnowledgeDocument
from app.api.deps import get_current_user, get_db
from app.api.routes import workspaces, tasks, meetings, documents, search, chat, integrations, users
from app.models.chat import ChatMessage, ChatRole
from app.services.pilot_phase1 import execute_explicit_task_command, _verified_participant
from app.services.knowledge_retriever import KnowledgeRetriever
from app.services.pilot_identity import resolve_provider_identity
from app.services.workspace_join import hash_join_code
from app.models.notification import Notification, NotificationType
from app.services.pilot_runtime import execute_pilot_query
from app.services.pilot_observability import PilotTrace


@compiles(ARRAY, "sqlite")
@compiles(JSONB, "sqlite")
@compiles(Vector, "sqlite")
def sqlite_test_type(element, compiler, **kwargs):
    return "TEXT"


class WorkspaceRBAC(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.owner, self.manager, self.member, self.other, self.outsider = [
            User(id=uuid.uuid4(), clerk_id="user_" + uuid.uuid4().hex, name=name,
                 email=f"{name.lower()}@example.com", email_verified=True)
            for name in ("Owner", "Manager", "Alice", "Bob", "Outsider")]
        self.db.add_all([self.owner, self.manager, self.member, self.other, self.outsider]); self.db.flush()
        self.ws = Workspace(id=uuid.uuid4(), name="Engineering", owner_id=self.owner.id)
        self.foreign = Workspace(id=uuid.uuid4(), name="Other Company", owner_id=self.outsider.id)
        self.db.add_all([self.ws, self.foreign]); self.db.flush()
        for user, role in ((self.owner, WorkspaceRole.owner), (self.manager, WorkspaceRole.admin), (self.member, WorkspaceRole.member), (self.other, WorkspaceRole.member)):
            self.db.add(WorkspaceMember(workspace_id=self.ws.id, user_id=user.id, role=role))
        self.db.add(WorkspaceMember(workspace_id=self.foreign.id, user_id=self.outsider.id, role=WorkspaceRole.owner))
        self.meeting = Meeting(id=uuid.uuid4(), workspace_id=self.ws.id, title="Shared Meeting", created_by=self.owner.id, status=MeetingStatus.completed)
        self.foreign_meeting = Meeting(id=uuid.uuid4(), workspace_id=self.foreign.id, title="Private Other Company", created_by=self.outsider.id, status=MeetingStatus.completed)
        self.db.add_all([self.meeting, self.foreign_meeting]); self.db.flush()
        self.mine = Task(id=uuid.uuid4(), meeting_id=self.meeting.id, title="review Alice PR", assignee_id=self.member.id, assignee_name="Alice")
        self.theirs = Task(id=uuid.uuid4(), meeting_id=self.meeting.id, title="review Bob PR", assignee_id=self.other.id, assignee_name="Bob")
        self.unassigned = Task(id=uuid.uuid4(), meeting_id=self.meeting.id, title="review unassigned PR", assignee_name="Alice")
        self.foreign_task = Task(id=uuid.uuid4(), meeting_id=self.foreign_meeting.id, title="review foreign PR", assignee_id=self.member.id)
        self.doc = KnowledgeDocument(id=uuid.uuid4(), workspace_id=self.ws.id, title="Company Policy", filename="policy.txt", file_type="txt", status="ready", created_by=self.owner.id)
        self.db.add_all([self.mine, self.theirs, self.unassigned, self.foreign_task, self.doc]); self.db.commit()
        self.actor = self.member
        self.app = FastAPI()
        for route in (workspaces.router, tasks.router, meetings.router, documents.router, search.router, chat.router, integrations.router, users.router):
            self.app.include_router(route)
        self.app.dependency_overrides[get_current_user] = lambda: self.actor
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close(); self.db.close(); self.engine.dispose()

    def test_every_approved_member_reads_workspace_meetings_but_outsiders_cannot(self):
        response = self.client.get(f"/api/v1/meetings/{self.meeting.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workspace_id"], str(self.ws.id))
        self.actor = self.owner
        response = self.client.patch(f"/api/v1/meetings/{self.meeting.id}", json={"title": "Updated meeting"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workspace_id"], str(self.ws.id))
        self.actor = self.member
        self.assertEqual(self.client.get(f"/api/v1/meetings/{self.foreign_meeting.id}").status_code, 403)
        roles = self.client.get("/api/v1/workspaces").json()
        self.assertEqual(roles[0]["current_role"], "member")

    def test_task_lists_and_search_include_only_own_verified_assignments(self):
        for path in (f"/api/v1/tasks?workspace_id={self.ws.id}", f"/api/v1/meetings/{self.meeting.id}/tasks"):
            self.assertEqual([row["id"] for row in self.client.get(path).json()], [str(self.mine.id)])
        with patch("app.api.routes.search.embed_text", return_value=None):
            results = self.client.get(f"/api/v1/search?q=review&filter_type=tasks&workspace_id={self.ws.id}").json()["results"]
        self.assertEqual(len(results), 1); self.assertIn("Alice", results[0]["snippet"])

    def test_rag_task_evidence_is_filtered_before_prompt(self):
        with patch("app.services.knowledge_retriever.embed_text", return_value=None):
            evidence = KnowledgeRetriever(self.db, self.ws.id, self.member.id).retrieve("review")
        self.assertEqual([item.id for item in evidence], [f"task:{self.mine.id}"])

    def test_member_changes_only_own_status_never_assignment_or_other_task(self):
        url = f"/api/v1/tasks/{self.mine.id}"
        self.assertEqual(self.client.patch(url, json={"status": "done"}).status_code, 200)
        for data in ({"title": "changed"}, {"assignee_id": str(self.other.id)}, {"assignee_name": None}, {"due_date": "2026-10-09"}):
            self.assertEqual(self.client.patch(url, json=data).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/v1/tasks/{self.theirs.id}", json={"status": "done"}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/tasks", json={"meeting_id": str(self.meeting.id), "title": "create unauthorized task"}).status_code, 403)

    def test_managers_manage_tasks_and_members_cannot_manage_documents(self):
        self.assertEqual(self.client.get(f"/api/v1/documents?workspace_id={self.ws.id}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/documents/{self.doc.id}").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/documents/upload", data={"workspace_id": str(self.ws.id)}, files={"file": ("x.txt", b"text", "text/plain")}).status_code, 403)
        self.actor = self.manager
        self.assertEqual(len(self.client.get(f"/api/v1/tasks?workspace_id={self.ws.id}").json()), 3)
        self.assertEqual(self.client.patch(f"/api/v1/tasks/{self.theirs.id}", json={"assignee_id": str(self.member.id)}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/documents/{self.doc.id}").status_code, 200)

    def test_owner_cannot_be_demoted_and_only_owner_may_promote_managers(self):
        self.actor = self.manager
        for uid, role in ((self.owner.id, "member"), (self.member.id, "admin"), (self.member.id, "owner"), (self.manager.id, "member")):
            self.assertEqual(self.client.patch(f"/api/v1/workspaces/{self.ws.id}/members/{uid}", json={"role": role}).status_code, 403)
        self.actor = self.owner
        self.assertEqual(self.client.patch(f"/api/v1/workspaces/{self.ws.id}/members/{self.member.id}", json={"role": "admin"}).status_code, 200)

    def test_code_request_is_not_membership_and_only_scoped_manager_can_approve(self):
        self.assertEqual(self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-code").status_code, 403)
        self.actor = self.owner
        code = self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-code").json()["code"]
        self.assertNotEqual(self.db.get(Workspace, self.ws.id).join_code_hash, code)
        self.actor = self.outsider
        request = self.client.post("/api/v1/workspaces/join", json={"code": code}).json()
        self.assertEqual(request["status"], "pending")
        self.assertIsNone(self.db.get(WorkspaceMember, (self.ws.id, self.outsider.id)))
        self.assertEqual(self.client.get(f"/api/v1/meetings/{self.meeting.id}").status_code, 403)
        review = f"/api/v1/workspaces/{self.ws.id}/join-requests/{request['id']}/review"
        self.assertEqual(self.client.post(review, json={"decision": "approve"}).status_code, 403)
        self.actor = self.owner
        self.assertEqual(self.client.post(f"/api/v1/workspaces/{self.foreign.id}/join-requests/{request['id']}/review", json={"decision": "approve"}).status_code, 403)
        self.assertEqual(self.client.post(review, json={"decision": "approve"}).status_code, 200)
        self.assertEqual(self.client.post(review, json={"decision": "reject"}).status_code, 409)
        self.actor = self.outsider
        self.assertEqual(self.client.get(f"/api/v1/meetings/{self.meeting.id}").status_code, 200)
        self.assertEqual(self.db.get(WorkspaceMember, (self.ws.id, self.outsider.id)).role, WorkspaceRole.member)

    def test_rotation_expiry_rejection_and_duplicate_pending(self):
        self.actor = self.owner
        old = self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-code").json()["code"]
        code = self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-code").json()["code"]
        self.actor = self.outsider
        self.assertEqual(self.client.post("/api/v1/workspaces/join", json={"code": old}).status_code, 404)
        first = self.client.post("/api/v1/workspaces/join", json={"code": code}).json()
        second = self.client.post("/api/v1/workspaces/join", json={"code": code}).json()
        self.assertEqual(first["id"], second["id"])
        self.actor = self.owner
        self.assertEqual(self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-requests/{first['id']}/review", json={"decision": "reject"}).status_code, 200)
        self.actor = self.outsider
        self.assertEqual(self.client.post("/api/v1/workspaces/join", json={"code": code}).status_code, 409)
        self.ws.join_code_expires_at = datetime.now(timezone.utc) - timedelta(days=1); self.db.commit()
        self.assertEqual(self.client.post("/api/v1/workspaces/join", json={"code": code}).status_code, 404)

    def test_same_name_or_unverified_email_does_not_prove_provider_identity(self):
        unknown = resolve_provider_identity(self.db, self.meeting, provider="google_meet", email=self.member.email, email_verified=False)
        self.assertIsNone(unknown.user_id)
        known = resolve_provider_identity(self.db, self.meeting, provider="google_meet", email=self.member.email, email_verified=True)
        self.assertEqual(known.user_id, self.member.id)
        self.member.email_verified = False; self.db.commit()
        self.assertIsNone(resolve_provider_identity(self.db, self.meeting, provider="google_meet", email=self.member.email, email_verified=True).user_id)

    def test_manager_confirmation_scoped_and_nonmanager_cannot_bind_identity(self):
        participant = MeetingParticipant(meeting_id=self.meeting.id, name="Alice on Meet")
        self.db.add(participant); self.db.commit()
        path = f"/api/v1/meetings/{self.meeting.id}/identities"
        body = {"speaker_label": participant.name, "user_id": str(self.member.id)}
        self.assertEqual(self.client.patch(path, json=body).status_code, 403)
        self.actor = self.manager
        self.assertEqual(self.client.patch(path, json={**body, "user_id": str(self.outsider.id)}).status_code, 422)
        result = self.client.patch(path, json=body)
        self.assertEqual(result.status_code, 200); self.assertEqual(result.json()["evidence"], "manager_confirmed")

    def test_members_cannot_edit_shared_analysis_or_someone_elses_meeting(self):
        path = f"/api/v1/meetings/{self.meeting.id}"
        for url, body in ((path, {"title": "Changed"}), (path + "/summary", {"overview": "Changed summary"})):
            self.assertEqual(self.client.patch(url, json=body).status_code, 403)
        self.assertEqual(self.client.delete(path).status_code, 403)

    def test_pilot_task_commands_obey_manager_roles_and_chat_history_is_personal(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as denied:
            execute_explicit_task_command(self.db, self.meeting.id, self.member, "Hey Pilot, create a task for Bob to review the PR")
        self.assertEqual(denied.exception.status_code, 403)
        self.db.add_all([ChatMessage(meeting_id=self.meeting.id, user_id=self.member.id, role=ChatRole.assistant, content="Alice's private query result"),
                         ChatMessage(meeting_id=self.meeting.id, user_id=self.other.id, role=ChatRole.assistant, content="Bob's private query result"),
                         ChatMessage(meeting_id=self.meeting.id, user_id=None, role=ChatRole.assistant, content="Legacy unattributed private result")])
        self.db.commit()
        rows = self.client.get(f"/api/v1/meetings/{self.meeting.id}/chat").json()
        self.assertEqual([row["content"] for row in rows], ["Alice's private query result"])

    def test_removal_revokes_reads_and_old_approval_cannot_reenter_without_review(self):
        self.actor = self.owner
        code = self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-code").json()["code"]
        self.actor = self.outsider
        pending = self.client.post("/api/v1/workspaces/join", json={"code": code}).json()
        self.actor = self.owner
        self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-requests/{pending['id']}/review", json={"decision": "approve"})
        self.assertEqual(self.client.delete(f"/api/v1/workspaces/{self.ws.id}/members/{self.outsider.id}").status_code, 204)
        self.actor = self.outsider
        self.assertEqual(self.client.get(f"/api/v1/meetings/{self.meeting.id}").status_code, 403)
        history = self.client.get("/api/v1/workspaces/join-requests").json()
        self.assertEqual(history[0]["status"], "removed")
        result = self.client.post("/api/v1/workspaces/join", json={"code": code}).json()
        self.assertEqual(result["status"], "pending")
        self.assertIsNone(self.db.get(WorkspaceMember, (self.ws.id, self.outsider.id)))

    def test_disabled_code_blocks_new_requests_but_existing_request_needs_review(self):
        path = f"/api/v1/workspaces/{self.ws.id}/join-code"
        self.actor = self.owner
        code = self.client.post(path).json()["code"]
        self.actor = self.outsider
        request = self.client.post("/api/v1/workspaces/join", json={"code": code}).json()
        self.assertEqual(self.client.delete(path).status_code, 403)
        self.actor = self.manager
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.actor = self.outsider
        self.assertEqual(self.client.post("/api/v1/workspaces/join", json={"code": code}).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/workspaces/join-requests").json()[0]["status"], "pending")
        self.assertIsNone(self.db.get(WorkspaceMember, (self.ws.id, self.outsider.id)))
        self.actor = self.manager
        self.assertEqual(self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-requests/{request['id']}/review", json={"decision": "approve"}).status_code, 200)

    def test_cached_manager_role_cannot_survive_demotion(self):
        self.actor = self.manager
        cached = self.db.get(WorkspaceMember, (self.ws.id, self.manager.id))
        self.assertEqual(cached.role, WorkspaceRole.admin)
        self.db.execute(update(WorkspaceMember).where(WorkspaceMember.workspace_id == self.ws.id,
            WorkspaceMember.user_id == self.manager.id).values(role=WorkspaceRole.member).execution_options(synchronize_session=False))
        self.db.flush()
        self.assertEqual(cached.role, WorkspaceRole.admin)
        self.assertEqual(self.client.post(f"/api/v1/workspaces/{self.ws.id}/join-code").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/v1/documents/{self.doc.id}").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/v1/tasks/{self.theirs.id}", json={"status": "done"}).status_code, 403)

    def test_creator_tag_is_not_proof_of_speaker_identity(self):
        self.db.add(MeetingParticipant(meeting_id=self.meeting.id, name=self.owner.name, user_id=self.owner.id))
        self.db.commit()
        self.assertIsNone(_verified_participant(self.db, self.meeting, self.owner.name))
        self.actor = self.owner
        path = f"/api/v1/meetings/{self.meeting.id}/identities"
        before = self.client.get(path).json()[0]
        self.assertIsNone(before["user_id"])
        self.assertEqual(before["evidence"], "unverified")
        self.assertEqual(self.client.patch(path, json={"speaker_label": self.owner.name, "user_id": str(self.owner.id)}).status_code, 200)
        self.assertEqual(_verified_participant(self.db, self.meeting, self.owner.name).id, self.owner.id)

    def test_duplicate_speaker_labels_cannot_be_bound_by_name(self):
        self.db.add_all([MeetingParticipant(meeting_id=self.meeting.id, name="Alice"),
                         MeetingParticipant(meeting_id=self.meeting.id, name="alice")])
        self.db.commit()
        self.actor = self.owner
        path = f"/api/v1/meetings/{self.meeting.id}/identities"
        self.assertTrue(all(row["ambiguous"] for row in self.client.get(path).json()))
        self.assertEqual(self.client.patch(path, json={"speaker_label": "Alice", "user_id": str(self.member.id)}).status_code, 409)
        self.assertIsNone(_verified_participant(self.db, self.meeting, "Alice"))
        self.assertEqual(self.client.patch(path, json={"speaker_label": "   ", "user_id": str(self.member.id)}).status_code, 422)

    def test_zoom_cloud_library_is_manager_only_and_never_called_for_member(self):
        path = f"/api/v1/integrations/workspace/{self.ws.id}/zoom"
        with patch("app.api.routes.integrations.list_zoom_cloud_recordings", return_value=[]) as listing, \
             patch("app.api.routes.integrations.import_zoom_cloud_recording") as importing:
            self.assertEqual(self.client.get(path + "/recordings").status_code, 403)
            self.assertEqual(self.client.post(path + "/import", json={"topic": "Private cloud recording", "download_url": "https://example.test/audio"}).status_code, 403)
            listing.assert_not_called(); importing.assert_not_called()
            self.actor = self.manager
            self.assertEqual(self.client.get(path + "/recordings").status_code, 200)
            listing.assert_called_once()

    def test_removed_members_cannot_read_previous_meeting_notifications(self):
        self.db.add(Notification(user_id=self.member.id, meeting_id=self.meeting.id, type=NotificationType.meeting_processed))
        self.db.commit()
        self.assertEqual(len(self.client.get("/api/v1/users/notifications").json()), 1)
        self.actor = self.owner
        self.assertEqual(self.client.delete(f"/api/v1/workspaces/{self.ws.id}/members/{self.member.id}").status_code, 204)
        self.actor = self.member
        self.assertEqual(self.client.get("/api/v1/users/notifications").json(), [])

    def test_workspace_creation_is_explicit_and_rejects_privilege_fields(self):
        self.db.delete(self.db.get(WorkspaceMember, (self.foreign.id, self.outsider.id))); self.db.commit()
        self.actor = self.outsider
        self.assertEqual(self.client.get("/api/v1/workspaces").json(), [])
        self.assertEqual(self.client.post("/api/v1/workspaces", json={"name": "  "}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/workspaces", json={"name": "A company", "owner_id": str(self.owner.id)}).status_code, 422)
        created = self.client.post("/api/v1/workspaces", json={"name": "  My company  "})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["name"], "My company")
        self.assertEqual(created.json()["owner_id"], str(self.outsider.id))
        self.assertEqual(created.json()["current_role"], "owner")

    def test_email_invites_reject_ambiguous_case_variant_accounts(self):
        self.actor = self.owner
        self.db.add(User(id=uuid.uuid4(), clerk_id="case_variant", name="Other outsider", email=self.outsider.email.upper(), email_verified=True))
        self.db.commit()
        result = self.client.post(f"/api/v1/workspaces/{self.ws.id}/invite", json={"email": self.outsider.email})
        self.assertEqual(result.status_code, 409)
        self.assertIsNone(self.db.get(WorkspaceMember, (self.ws.id, self.outsider.id)))

    def test_pilot_task_queries_obey_role_and_explicit_personal_scope(self):
        def query(user, question):
            return execute_pilot_query(self.db, self.meeting.id, self.ws.id, user, question,
                "Hey Pilot", PilotTrace(self.meeting.id, self.ws.id))
        personal = query(self.member, "Show my tasks")
        self.assertEqual([c["task_id"] for c in personal["citations"]], [str(self.mine.id)])
        for actor, expected in ((self.member, {str(self.mine.id)}), (self.manager, {str(self.mine.id), str(self.theirs.id), str(self.unassigned.id)})):
            result = query(actor, "Show the task list")
            self.assertEqual({c["task_id"] for c in result["citations"]}, expected)
        self.assertEqual(query(self.manager, "Show my tasks")["citations"], [])
        self.mine.status = TaskStatus.done; self.db.commit()
        self.assertEqual(query(self.member, "Show open tasks")["citations"], [])

    def test_unregistered_request_cannot_self_assign_manager_or_owner(self):
        self.actor = self.outsider
        self.assertEqual(self.client.post("/api/v1/workspaces/join", json={"code": "unknown_code_123456789", "role": "owner"}).status_code, 422)
        self.app.dependency_overrides.pop(get_current_user)
        self.assertEqual(self.client.post("/api/v1/workspaces/join", json={"code": "unknown_code_123456789"}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
