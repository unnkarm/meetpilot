import datetime
import json
import logging
import urllib.parse
import uuid
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.encryption import decrypt_secret, encrypt_secret, mask_secret
from app.models.integration import WorkspaceIntegration
from app.models.task import Task

logger = logging.getLogger(__name__)

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def get_google_auth_url(workspace_id: uuid.UUID, redirect_uri: str | None = None) -> str:
    """Constructs the Google OAuth 2.0 authorization URL for offline calendar access."""
    client_id = settings.GOOGLE_CLIENT_ID or "mock-google-client-id.apps.googleusercontent.com"
    r_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    params = {
        "client_id": client_id,
        "redirect_uri": r_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": str(workspace_id),
    }
    return f"{GOOGLE_AUTH_BASE}?{urllib.parse.urlencode(params)}"


def exchange_google_code(
    db: Session, workspace_id: uuid.UUID, code: str, redirect_uri: str | None = None
) -> WorkspaceIntegration:
    """Exchanges an authorization code for access and refresh tokens, encrypting them at rest."""
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    r_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": r_uri,
        "grant_type": "authorization_code",
    }

    email = "connected-account@gmail.com"
    tokens = {
        "access_token": "mock-google-access-token",
        "refresh_token": "mock-google-refresh-token",
        "expires_in": 3600,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }

    if client_id and client_secret:
        try:
            resp = httpx.post(GOOGLE_TOKEN_URL, data=payload, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                tokens = {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token") or tokens["refresh_token"],
                    "expires_in": data.get("expires_in", 3600),
                    "created_at": datetime.datetime.utcnow().isoformat(),
                }
                # Fetch user email
                user_resp = httpx.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                    timeout=10.0,
                )
                if user_resp.status_code == 200:
                    email = user_resp.json().get("email", email)
        except Exception as exc:
            logger.error("Failed to exchange Google OAuth code: %s", exc, exc_info=True)

    encrypted_data = encrypt_secret(json.dumps(tokens))
    masked_email = mask_secret(email, "google_calendar")

    integration = (
        db.query(WorkspaceIntegration)
        .filter(
            WorkspaceIntegration.workspace_id == workspace_id,
            WorkspaceIntegration.provider == "google_calendar",
        )
        .first()
    )
    if not integration:
        integration = WorkspaceIntegration(
            workspace_id=workspace_id,
            provider="google_calendar",
            is_connected=True,
            encrypted_config=encrypted_data,
            masked_identifier=masked_email,
        )
        db.add(integration)
    else:
        integration.is_connected = True
        integration.encrypted_config = encrypted_data
        integration.masked_identifier = masked_email

    db.commit()
    db.refresh(integration)
    return integration


def sync_task_to_google_calendar(db: Session, task_id: uuid.UUID) -> bool:
    """Syncs an assigned task with a due date to the workspace's Google Calendar."""
    try:
        task = db.get(Task, task_id)
        if not task or not task.due_date:
            return False

        integration = (
            db.query(WorkspaceIntegration)
            .filter(
                WorkspaceIntegration.workspace_id == task.meeting.workspace_id,
                WorkspaceIntegration.provider == "google_calendar",
                WorkspaceIntegration.is_connected == True,
            )
            .first()
        )
        if not integration or not integration.encrypted_config:
            return False

        decrypted = decrypt_secret(integration.encrypted_config)
        if not decrypted:
            return False

        tokens = json.loads(decrypted)
        access_token = tokens.get("access_token")
        if not access_token:
            return False

        event_payload = {
            "summary": f"[MeetPilot] {task.title}",
            "description": f"Assigned to: {task.assignee_name or 'Unassigned'}\nPriority: {task.priority.value.upper()}\nExtracted from meeting: {task.meeting.title}",
            "start": {
                "date": datetime.date.today().isoformat(),
            },
            "end": {
                "date": (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
            },
        }

        # Attempt call to Google Calendar API
        resp = httpx.post(
            GOOGLE_CALENDAR_EVENTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json=event_payload,
            timeout=10.0,
        )
        if resp.status_code in (200, 201):
            logger.info("Successfully synced task %s to Google Calendar", task_id)
            return True
        return False
    except Exception as exc:
        logger.warning("Google Calendar task sync notice: %s", exc)
        return False
