"""Offline SQL/HTTP checks; no bot, Docker, inference or external identity calls."""
import unittest
import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # register foreign keys
from app.api.deps import get_current_user, get_db
from app.api.routes import legal, live_meetings, meetings
from app.core.config import settings
from app.database.base import Base
from app.models.meeting import Meeting
from app.models.product_event import ProductEvent
from app.models.transcript import Vector
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.services.legal_policies import policy_metadata, POLICY_VERSION


@compiles(ARRAY, "sqlite")
@compiles(JSONB, "sqlite")
@compiles(Vector, "sqlite")
def sqlite_test_type(element, compiler, **kwargs):
    return "TEXT"


class LegalPolicies(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.owner = User(id=uuid.uuid4(), clerk_id="legal-owner", name="Owner", email="owner@example.test")
        self.other = User(id=uuid.uuid4(), clerk_id="legal-other", name="Other", email="other@example.test")
        self.db.add_all([self.owner, self.other]); self.db.flush()
        self.workspace = Workspace(id=uuid.uuid4(), name="Legal test", owner_id=self.owner.id)
        self.db.add(self.workspace); self.db.flush()
        self.db.add(WorkspaceMember(workspace_id=self.workspace.id, user_id=self.owner.id, role=WorkspaceRole.owner))
        self.db.commit()
        self.actor = self.owner
        app = FastAPI()
        for router in (legal.router, live_meetings.router, meetings.router):
            app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.actor
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close(); self.db.close(); self.engine.dispose()

    def acknowledge(self, **overrides):
        payload = dict(bundle=policy_metadata()["bundle"], terms_agreed=True, privacy_acknowledged=True,
                       recording_responsibilities_acknowledged=True)
        return self.client.post("/api/v1/legal/acceptance", json={**payload, **overrides})

    def start(self, **overrides):
        payload = dict(workspace_id=str(self.workspace.id), meeting_url="https://meet.google.com/abc-defg-hij",
                       recording_authorized=True, recording_policy_version=POLICY_VERSION)
        return self.client.post("/api/v1/meetings/live/start", json={**payload, **overrides})

    def test_receipt_is_versioned_idempotent_and_account_scoped(self):
        self.assertFalse(self.client.get("/api/v1/legal/acceptance").json()["accepted"])
        self.assertEqual(self.acknowledge().status_code, 200)
        self.assertEqual(self.acknowledge().status_code, 200)
        self.assertEqual(self.db.query(ProductEvent).count(), 1)
        receipt = self.db.query(ProductEvent).one()
        self.assertIsNotNone(receipt.created_at)
        self.assertEqual(receipt.properties["versions"]["terms"], POLICY_VERSION)
        self.assertTrue(self.client.get("/api/v1/legal/acceptance").json()["accepted"])
        self.actor = self.other
        self.assertFalse(self.client.get("/api/v1/legal/acceptance").json()["accepted"])

    def test_missing_false_or_coerced_acknowledgments_are_rejected(self):
        for field in ("terms_agreed", "privacy_acknowledged", "recording_responsibilities_acknowledged"):
            for value in (False, 1, "true", None):
                self.assertEqual(self.acknowledge(**{field: value}).status_code, 422)
        self.assertEqual(self.acknowledge(user_id=str(self.other.id)).status_code, 422)
        self.assertEqual(self.db.query(ProductEvent).count(), 0)

    def test_stale_first_acceptance_is_rejected_but_later_changes_never_reprompt(self):
        self.assertEqual(self.acknowledge(bundle="old").status_code, 409)
        self.acknowledge()
        original = self.client.get("/api/v1/legal/acceptance").json()
        with patch.object(settings, "LEGAL_OPERATOR_NAME", "New operator"):
            changed = self.client.get("/api/v1/legal/acceptance").json()
            self.assertTrue(changed["accepted"])
            self.assertNotEqual(changed["policies"]["bundle"], original["policies"]["bundle"])
            self.assertEqual(changed["accepted_bundle"], original["accepted_bundle"])
            self.assertEqual(self.acknowledge().json()["bundle"], original["accepted_bundle"])
        with patch("app.services.legal_policies.POLICY_VERSION", "future-version"):
            self.assertTrue(self.client.get("/api/v1/legal/acceptance").json()["accepted"])
            self.assertEqual(self.acknowledge().status_code, 200)
        self.assertEqual(self.db.query(ProductEvent).count(), 1)

    def test_public_metadata_is_allowlisted_and_incomplete_profiles_stay_drafts(self):
        with patch.object(settings, "LEGAL_POLICIES_PUBLISHED", True), patch.object(settings, "LEGAL_PRIVACY_EMAIL", ""):
            response = self.client.get("/api/v1/legal/policies")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        data = response.json()
        self.assertFalse(data["published"])
        self.assertEqual(set(data), {"versions", "operator", "published", "bundle"})
        self.assertEqual(set(data["operator"]), {"name", "address", "privacy_email", "jurisdiction", "processing", "retention"})

    def test_live_start_requires_account_acknowledgment_before_dispatch(self):
        with patch("app.api.routes.live_meetings.VexaClient") as vexa:
            self.assertEqual(self.start().status_code, 428)
            vexa.assert_not_called()
        self.assertEqual(self.db.query(Meeting).count(), 0)

    def test_membership_is_checked_before_legal_state(self):
        self.actor = self.other
        self.assertEqual(self.start(recording_authorized=False).status_code, 403)

    def test_acknowledged_live_start_keeps_vexa_without_collecting_repeated_consent(self):
        self.acknowledge()
        with patch("app.api.routes.live_meetings.VexaClient") as vexa, patch("app.api.routes.live_meetings.run_vexa_meeting_bot_task") as worker:
            response = self.start()
            self.assertEqual(response.status_code, 201, response.text)
            vexa.return_value.preflight.assert_called_once()
            worker.apply_async.assert_called_once()
        event = self.db.query(ProductEvent).filter(ProductEvent.name == "recording_policy_applied").one()
        self.assertEqual(event.workspace_id, self.workspace.id)
        self.assertEqual(event.user_id, self.owner.id)
        self.assertEqual(event.properties["meeting_id"], response.json()["id"])
        self.assertIs(event.properties["participant_consent_verified"], False)
        self.assertIs(event.properties["per_recording_authorization_collected"], False)
        self.assertIsNotNone(event.properties["account_acknowledgment_id"])

    def test_upload_requires_first_acknowledgment_and_then_no_repeated_fields(self):
        data = {"workspace_id": str(self.workspace.id), "title": "Test"}
        with patch("app.api.routes.meetings.save_upload") as storage, patch("app.api.routes.meetings.process_meeting") as worker:
            self.assertEqual(self.client.post("/api/v1/meetings/upload", data=data, files={"file": ("test.wav", b"test", "audio/wav")}).status_code, 428)
            storage.assert_not_called(); worker.delay.assert_not_called()
            self.acknowledge()
            storage.return_value = "local://test.wav"
            response = self.client.post("/api/v1/meetings/upload", data=data, files={"file": ("test.wav", b"test", "audio/wav")})
            self.assertEqual(response.status_code, 201, response.text)
            worker.delay.assert_called_once()


if __name__ == "__main__":
    unittest.main()
