import logging
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_clerk_token
from app.database.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/me", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    clerk_payload = verify_clerk_token(token)
    if not clerk_payload:
        raise credentials_exception

    clerk_id = clerk_payload.get("sub")
    if not clerk_id:
        raise credentials_exception

    # 1. Extract profile fields from Clerk JWT claims
    email = (
        clerk_payload.get("email")
        or clerk_payload.get("primary_email_address")
        or clerk_payload.get("email_address")
    )
    name = (
        clerk_payload.get("name")
        or clerk_payload.get("full_name")
        or clerk_payload.get("first_name")
        or clerk_payload.get("username")
    )
    avatar_url = (
        clerk_payload.get("picture")
        or clerk_payload.get("image_url")
        or clerk_payload.get("avatar_url")
    )

    # 2. Check authenticated client headers sent by Frontend SDK
    header_email = request.headers.get("x-user-email")
    header_name = request.headers.get("x-user-name")
    header_avatar = request.headers.get("x-user-avatar")

    if header_email and "@" in header_email:
        email = header_email
    if header_name and header_name.strip():
        name = header_name.strip()
    if header_avatar and header_avatar.startswith("http"):
        avatar_url = header_avatar

    # 3. If email/name still empty and CLERK_SECRET_KEY is configured, fetch directly from Clerk API
    if (not email or not name or f"{clerk_id}" in str(email)) and settings.CLERK_SECRET_KEY:
        try:
            import httpx
            res = httpx.get(
                f"https://api.clerk.com/v1/users/{clerk_id}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                timeout=4.0,
            )
            if res.status_code == 200:
                c_data = res.json()
                primary_id = c_data.get("primary_email_address_id")
                for e in c_data.get("email_addresses", []):
                    if e.get("id") == primary_id:
                        email = e.get("email_address")
                        break
                if not email and c_data.get("email_addresses"):
                    email = c_data["email_addresses"][0].get("email_address")
                first = c_data.get("first_name") or ""
                last = c_data.get("last_name") or ""
                full = f"{first} {last}".strip()
                if full:
                    name = full
                elif c_data.get("username"):
                    name = c_data["username"]
                if c_data.get("image_url"):
                    avatar_url = c_data["image_url"]
        except Exception as err:
            logger.warning(f"Clerk backend user API lookup note: {err}")

    # Clean fallback defaults if profile claims are totally absent
    if not email:
        email = f"{clerk_id}@clerk.user"
    if not name or name == email.split("@")[0]:
        name = email.split("@")[0]

    # Query DB by clerk_id or email
    user = db.query(User).filter((User.clerk_id == clerk_id) | (User.email == email)).first()
    if user:
        updated = False
        if user.clerk_id != clerk_id:
            user.clerk_id = clerk_id
            updated = True
        if name and user.name != name and not user.name.startswith("user_"):
            user.name = name
            updated = True
        elif user.name.startswith("user_") and name and not name.startswith("user_"):
            user.name = name
            updated = True
        if email and user.email != email and not email.endswith("@clerk.user"):
            user.email = email
            updated = True
        elif user.email.endswith("@clerk.user") and email and not email.endswith("@clerk.user"):
            user.email = email
            updated = True
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            updated = True
        if updated:
            try:
                db.commit()
                db.refresh(user)
            except Exception:
                db.rollback()
        return user

    # Auto-provision user on first Clerk login (Just-In-Time)
    try:
        new_user = User(
            id=uuid.uuid4(),
            clerk_id=clerk_id,
            name=name,
            email=email,
            avatar_url=avatar_url,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        # Retry query in case of parallel creation race
        retry_user = db.query(User).filter((User.clerk_id == clerk_id) | (User.email == email)).first()
        if retry_user:
            return retry_user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synchronize user account with database: {str(e)}",
        )






def get_workspace_member(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMember:
    """Ensures the current user belongs to the given workspace, returning their membership."""
    membership = db.get(WorkspaceMember, (workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
    return membership


def require_role(*allowed_roles: WorkspaceRole):
    def _checker(membership: WorkspaceMember = Depends(get_workspace_member)) -> WorkspaceMember:
        if membership.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return membership

    return _checker


def get_user_workspace_ids(user: User, db: Session) -> list[uuid.UUID]:
    rows = db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == user.id).all()
    return [r[0] for r in rows]


def get_meeting_for_member(meeting_id: uuid.UUID, current_user: User, db: Session):
    """Loads a meeting and verifies the current user belongs to its workspace."""
    from app.models.meeting import Meeting  # local import avoids a circular import at module load time

    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    membership = db.get(WorkspaceMember, (meeting.workspace_id, current_user.id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this meeting's workspace")

    return meeting
