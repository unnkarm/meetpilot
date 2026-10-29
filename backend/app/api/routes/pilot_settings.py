"""Authenticated workspace voice selection and local preview audio."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_workspace_member, require_role
from app.database.session import get_db
from app.models.workspace import Workspace, WorkspaceRole
from app.services.pilot_tts import available_voices, get_tts_provider, require_voice, synthesize_wake_ack

router = APIRouter(prefix="/api/v1/workspaces", tags=["pilot"])


class VoiceSelection(BaseModel):
    voice_id: str = Field(min_length=1, max_length=32)


def workspace_or_404(db, workspace_id):
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def validate_voice(voice_id):
    try:
        return require_voice(voice_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{workspace_id}/pilot/settings")
def voice_settings(workspace_id: uuid.UUID, db: Session = Depends(get_db),
                   member=Depends(get_workspace_member)):
    workspace = workspace_or_404(db, workspace_id)
    return {"voice_id": workspace.pilot_voice_id, "voices": available_voices(),
            "can_edit": member.role in {WorkspaceRole.owner, WorkspaceRole.admin}}


@router.patch("/{workspace_id}/pilot/settings")
async def update_voice_settings(workspace_id: uuid.UUID, payload: VoiceSelection,
                                db: Session = Depends(get_db),
                                member=Depends(require_role(WorkspaceRole.owner, WorkspaceRole.admin))):
    workspace = workspace_or_404(db, workspace_id)
    workspace.pilot_voice_id = validate_voice(payload.voice_id)
    db.commit()
    # Prime the short acknowledgement now; a later wake does no model loading.
    await synthesize_wake_ack(workspace.pilot_voice_id)
    return {"voice_id": workspace.pilot_voice_id}


@router.post("/{workspace_id}/pilot/voice-preview")
async def voice_preview(workspace_id: uuid.UUID, payload: VoiceSelection,
                        db: Session = Depends(get_db), member=Depends(get_workspace_member)):
    workspace_or_404(db, workspace_id)
    voice_id = validate_voice(payload.voice_id)
    wav = await get_tts_provider(voice_id).synthesize("Yes sir. I'm Pilot, your meeting assistant.")
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "no-store"})
