import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_meeting_for_member
from app.database.session import get_db
from app.models.chat import ChatMessage, ChatRole
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatRequest, ChatResponse
from app.services.chat_service import answer_question

router = APIRouter(prefix="/api/v1/meetings", tags=["chat"])


@router.post("/{meeting_id}/chat", response_model=ChatResponse)
def chat_with_meeting(
    meeting_id: uuid.UUID,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    get_meeting_for_member(meeting_id, current_user, db)

    db.add(ChatMessage(meeting_id=meeting_id, user_id=current_user.id, role=ChatRole.user, content=payload.question))
    db.commit()

    answer, cited_timestamp = answer_question(db, meeting_id, payload.question)

    db.add(
        ChatMessage(
            meeting_id=meeting_id,
            user_id=None,
            role=ChatRole.assistant,
            content=answer,
            cited_timestamp=cited_timestamp,
        )
    )
    db.commit()

    return ChatResponse(answer=answer, cited_timestamp=cited_timestamp)


@router.get("/{meeting_id}/chat", response_model=list[ChatMessageOut])
def get_chat_history(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatMessage]:
    meeting = get_meeting_for_member(meeting_id, current_user, db)
    return meeting.chat_messages
