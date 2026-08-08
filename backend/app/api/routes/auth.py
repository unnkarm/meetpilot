from fastapi import APIRouter, Depends
from pydantic import BaseModel
import uuid

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class AuthSessionOut(BaseModel):
    user: UserOut
    clerk_id: str | None = None
    authenticated: bool = True


@router.get("/me", response_model=AuthSessionOut)
def get_auth_me(current_user: User = Depends(get_current_user)) -> AuthSessionOut:
    """Returns the authenticated user details synchronized with Clerk."""
    return AuthSessionOut(
        user=UserOut.model_validate(current_user),
        clerk_id=current_user.clerk_id,
        authenticated=True,
    )
