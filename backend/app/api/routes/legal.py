from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, StrictBool, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.legal_policies import accept_policies, current_acceptance, policy_metadata

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])


class PolicyAcceptance(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    bundle: str
    terms_agreed: StrictBool
    privacy_acknowledged: StrictBool
    recording_responsibilities_acknowledged: StrictBool

    @field_validator("terms_agreed", "privacy_acknowledged", "recording_responsibilities_acknowledged")
    @classmethod
    def must_acknowledge(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("An explicit acknowledgment is required")
        return value


@router.get("/policies")
def policies(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return policy_metadata()


@router.get("/acceptance")
def acceptance(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    metadata = policy_metadata()
    receipt = current_acceptance(db, user.id)
    return {"policies": metadata, "accepted": receipt is not None,
            "accepted_versions": receipt.properties.get("versions") if receipt else None,
            "accepted_bundle": receipt.properties.get("bundle") if receipt else None,
            "accepted_at": receipt.created_at if receipt else None}


@router.post("/acceptance")
def accept(payload: PolicyAcceptance, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    receipt = accept_policies(db, user.id, payload.bundle)
    return {"accepted": True, "accepted_at": receipt.created_at, "bundle": receipt.properties["bundle"],
            "accepted_versions": receipt.properties.get("versions")}
