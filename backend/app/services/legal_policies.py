"""Versioned user acknowledgments, separate from participants' recording consent."""
import hashlib
import json
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.product_event import ProductEvent
from app.models.user import User

POLICY_VERSION = "2026-10-12.1"
RECORDING_POLICY_VERSION = POLICY_VERSION


def policy_metadata() -> dict:
    # Explicit allowlist: never return the settings object or provider credentials.
    operator = {
        "name": settings.LEGAL_OPERATOR_NAME.strip(),
        "address": settings.LEGAL_OPERATOR_ADDRESS.strip(),
        "privacy_email": settings.LEGAL_PRIVACY_EMAIL.strip(),
        "jurisdiction": settings.LEGAL_JURISDICTION.strip(),
        "processing": settings.LEGAL_PROCESSING_DISCLOSURE.strip(),
        "retention": settings.LEGAL_RETENTION_DISCLOSURE.strip(),
    }
    published = bool(settings.LEGAL_POLICIES_PUBLISHED and all(operator.values()))
    versions = {"terms": POLICY_VERSION, "privacy": POLICY_VERSION, "recording": RECORDING_POLICY_VERSION}
    snapshot = {"versions": versions, "operator": operator, "published": published}
    bundle = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return {**snapshot, "bundle": bundle}


def _event_name(metadata: dict) -> str:
    return f"legal_ack:{metadata['bundle']}"


def current_acceptance(db: Session, user_id: uuid.UUID) -> ProductEvent | None:
    """An account acknowledges once; later revisions remain available in Settings."""
    return db.query(ProductEvent).filter(
        ProductEvent.user_id == user_id, ProductEvent.name.like("legal_ack:%"),
    ).order_by(ProductEvent.created_at.desc(), ProductEvent.id.desc()).first()


def accept_policies(db: Session, user_id: uuid.UUID, bundle: str) -> ProductEvent:
    metadata = policy_metadata()
    # Serialize the first acknowledgment across tabs. Existing receipts survive
    # document, disclosure and publication changes and are never rewritten.
    db.query(User).filter(User.id == user_id).with_for_update().one()
    receipt = current_acceptance(db, user_id)
    if receipt is not None:
        db.commit()
        db.refresh(receipt)
        return receipt
    if bundle != metadata["bundle"]:
        raise HTTPException(409, "Policies changed. Review the current pages and acknowledge them again.")
    if receipt is None:
        receipt = ProductEvent(user_id=user_id, name=_event_name(metadata), properties={
            **metadata, "terms_agreed": True, "privacy_acknowledged": True,
            "recording_responsibilities_acknowledged": True,
        })
        db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def require_policy_acceptance(db: Session, user_id: uuid.UUID) -> None:
    if current_acceptance(db, user_id) is None:
        raise HTTPException(428, "Acknowledge the MeetPilot policies once before your first action.")


def record_capture_policy(db: Session, user_id: uuid.UUID, workspace_id: uuid.UUID, meeting_id: uuid.UUID, source: str) -> None:
    receipt = current_acceptance(db, user_id)
    db.add(ProductEvent(user_id=user_id, workspace_id=workspace_id, name="recording_policy_applied", properties={
        "meeting_id": str(meeting_id), "source": source,
        "account_acknowledgment_id": str(receipt.id) if receipt else None,
        "accepted_policy_bundle": receipt.properties.get("bundle") if receipt else None,
        "accepted_versions": receipt.properties.get("versions") if receipt else None,
        "policy_bundle_at_capture": policy_metadata()["bundle"],
        "per_recording_authorization_collected": False, "participant_consent_verified": False,
    }))
