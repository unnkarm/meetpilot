"""Authenticated Phase 1 Pilot context and explicit action endpoints."""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.meeting import TaskOut
from app.services.pilot_phase1 import answer_live_context, build_live_context, execute_explicit_task_command

router = APIRouter(prefix="/api/v1/meetings", tags=["pilot"])
logger = logging.getLogger(__name__)


class PilotActionRequest(BaseModel):
    command: str = Field(min_length=12, max_length=600)


class PilotQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@router.get("/{meeting_id}/pilot/context")
def get_pilot_context(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return build_live_context(db, meeting_id, current_user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Pilot context unavailable meeting=%s", meeting_id)
        raise HTTPException(status_code=503, detail="Pilot context is temporarily unavailable") from exc


@router.post("/{meeting_id}/pilot/ask")
def ask_pilot_context(
    meeting_id: uuid.UUID,
    payload: PilotQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return answer_live_context(db, meeting_id, current_user, payload.question)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Pilot answer unavailable meeting=%s", meeting_id)
        raise HTTPException(status_code=503, detail="Pilot answer is temporarily unavailable") from exc


@router.post("/{meeting_id}/pilot/action", response_model=TaskOut)
def run_pilot_action(
    meeting_id: uuid.UUID,
    payload: PilotActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return execute_explicit_task_command(db, meeting_id, current_user, payload.command)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Pilot action unavailable meeting=%s", meeting_id)
        raise HTTPException(status_code=503, detail="Pilot action is temporarily unavailable") from exc
