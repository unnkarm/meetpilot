import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.encryption import encrypt_secret, mask_secret
from app.database.session import get_db
from app.models.integration import WorkspaceIntegration
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.services.google_calendar_service import exchange_google_code, get_google_auth_url
from app.services.zoom_service import (
    exchange_zoom_code,
    get_zoom_auth_url,
    import_zoom_cloud_recording,
    list_zoom_cloud_recordings,
)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


# --- Schemas ---

class IntegrationOut(BaseModel):
    provider: str
    is_connected: bool
    masked_identifier: Optional[str] = None
    updated_at: Optional[str] = None


class DiscordSetupRequest(BaseModel):
    webhook_url: str


class OAuthExchangeRequest(BaseModel):
    workspace_id: uuid.UUID
    code: str
    redirect_uri: Optional[str] = None


class ZoomImportRequest(BaseModel):
    topic: str
    download_url: str
    file_type: str = "M4A"


# --- Helper for Workspace Permissions ---

def _require_workspace_role(
    workspace_id: uuid.UUID,
    user: User,
    db: Session,
    allowed_roles: list[WorkspaceRole] | None = None,
) -> WorkspaceMember:
    membership = db.get(WorkspaceMember, (workspace_id, user.id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
    if allowed_roles and membership.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient workspace permissions")
    return membership


# --- Endpoints ---

@router.get("/workspace/{workspace_id}", response_model=list[IntegrationOut])
def get_workspace_integrations(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IntegrationOut]:
    _require_workspace_role(workspace_id, current_user, db)

    db_integrations = (
        db.query(WorkspaceIntegration)
        .filter(WorkspaceIntegration.workspace_id == workspace_id)
        .all()
    )
    integration_map = {i.provider: i for i in db_integrations}

    all_providers = ["discord", "google_calendar", "zoom", "linear"]
    results = []
    for prov in all_providers:
        item = integration_map.get(prov)
        if item:
            results.append(
                IntegrationOut(
                    provider=prov,
                    is_connected=item.is_connected,
                    masked_identifier=item.masked_identifier,
                    updated_at=item.updated_at.isoformat() if item.updated_at else None,
                )
            )
        else:
            results.append(
                IntegrationOut(
                    provider=prov,
                    is_connected=False,
                    masked_identifier=None,
                    updated_at=None,
                )
            )
    return results


@router.post("/workspace/{workspace_id}/discord", response_model=IntegrationOut)
def setup_discord_webhook(
    workspace_id: uuid.UUID,
    payload: DiscordSetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrationOut:
    _require_workspace_role(workspace_id, current_user, db, [WorkspaceRole.owner, WorkspaceRole.admin])

    url = payload.webhook_url.strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Discord Webhook URL. Format: https://discord.com/api/webhooks/{id}/{token}",
        )

    encrypted = encrypt_secret(json.dumps({"webhook_url": url}))
    masked = mask_secret(url, "discord")

    integration = (
        db.query(WorkspaceIntegration)
        .filter(
            WorkspaceIntegration.workspace_id == workspace_id,
            WorkspaceIntegration.provider == "discord",
        )
        .first()
    )
    if not integration:
        integration = WorkspaceIntegration(
            workspace_id=workspace_id,
            provider="discord",
            is_connected=True,
            encrypted_config=encrypted,
            masked_identifier=masked,
        )
        db.add(integration)
    else:
        integration.is_connected = True
        integration.encrypted_config = encrypted
        integration.masked_identifier = masked

    db.commit()
    db.refresh(integration)
    return IntegrationOut(
        provider="discord",
        is_connected=True,
        masked_identifier=masked,
        updated_at=integration.updated_at.isoformat() if integration.updated_at else None,
    )


@router.delete("/workspace/{workspace_id}/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_integration(
    workspace_id: uuid.UUID,
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _require_workspace_role(workspace_id, current_user, db, [WorkspaceRole.owner, WorkspaceRole.admin])

    integration = (
        db.query(WorkspaceIntegration)
        .filter(
            WorkspaceIntegration.workspace_id == workspace_id,
            WorkspaceIntegration.provider == provider,
        )
        .first()
    )
    if integration:
        db.delete(integration)
        db.commit()


# --- Google OAuth Routes ---

@router.get("/google/auth-url")
def google_auth_url(
    workspace_id: uuid.UUID = Query(...),
    redirect_uri: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_workspace_role(workspace_id, current_user, db, [WorkspaceRole.owner, WorkspaceRole.admin])
    url = get_google_auth_url(workspace_id, redirect_uri)
    return {"url": url}


@router.post("/google/callback", response_model=IntegrationOut)
def google_oauth_callback(
    payload: OAuthExchangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrationOut:
    _require_workspace_role(payload.workspace_id, current_user, db, [WorkspaceRole.owner, WorkspaceRole.admin])
    integration = exchange_google_code(db, payload.workspace_id, payload.code, payload.redirect_uri)
    return IntegrationOut(
        provider="google_calendar",
        is_connected=integration.is_connected,
        masked_identifier=integration.masked_identifier,
        updated_at=integration.updated_at.isoformat() if integration.updated_at else None,
    )


# --- Zoom OAuth Routes & Cloud Picker ---

@router.get("/zoom/auth-url")
def zoom_auth_url(
    workspace_id: uuid.UUID = Query(...),
    redirect_uri: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_workspace_role(workspace_id, current_user, db, [WorkspaceRole.owner, WorkspaceRole.admin])
    url = get_zoom_auth_url(workspace_id, redirect_uri)
    return {"url": url}


@router.post("/zoom/callback", response_model=IntegrationOut)
def zoom_oauth_callback(
    payload: OAuthExchangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrationOut:
    _require_workspace_role(payload.workspace_id, current_user, db, [WorkspaceRole.owner, WorkspaceRole.admin])
    integration = exchange_zoom_code(db, payload.workspace_id, payload.code, payload.redirect_uri)
    return IntegrationOut(
        provider="zoom",
        is_connected=integration.is_connected,
        masked_identifier=integration.masked_identifier,
        updated_at=integration.updated_at.isoformat() if integration.updated_at else None,
    )


@router.get("/workspace/{workspace_id}/zoom/recordings")
def get_zoom_recordings(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_workspace_role(workspace_id, current_user, db)
    recordings = list_zoom_cloud_recordings(db, workspace_id)
    return recordings


@router.post("/workspace/{workspace_id}/zoom/import", status_code=status.HTTP_201_CREATED)
def import_zoom_recording_endpoint(
    workspace_id: uuid.UUID,
    payload: ZoomImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_workspace_role(workspace_id, current_user, db)
    meeting = import_zoom_cloud_recording(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_avatar=current_user.avatar_url,
        topic=payload.topic,
        download_url=payload.download_url,
        file_type=payload.file_type,
    )
    return {
        "id": meeting.id,
        "title": meeting.title,
        "status": meeting.status,
        "message": "Zoom cloud recording successfully queued for AI processing!",
    }
