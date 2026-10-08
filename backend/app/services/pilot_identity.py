"""Provider identity resolution is separate from acoustic speaker labeling."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.app_config import APP_CONFIG
from app.models.meeting import Meeting, MeetingParticipant
from app.models.meeting_speaker_map import MeetingSpeakerMap
from app.models.user import User
from app.models.workspace import WorkspaceMember


@dataclass(frozen=True)
class IdentityResolution:
    user_id: uuid.UUID | None = None
    confidence: float = 0.0
    evidence: str = "unknown"


def resolve_provider_identity(
    db: Session, meeting: Meeting, *, provider: str,
    provider_user_id: str | None = None, email: str | None = None,
    email_verified: bool = False,
) -> IdentityResolution:
    """Resolve only identities backed by a prior provider binding or verified email."""
    provider = provider.strip().casefold()
    provider_user_id = (provider_user_id or "").strip()
    email = (email or "").strip().casefold()
    if not provider:
        return IdentityResolution()
    if provider_user_id:
        matches = (
            db.query(MeetingParticipant.user_id)
            .join(Meeting, Meeting.id == MeetingParticipant.meeting_id)
            .join(WorkspaceMember, WorkspaceMember.user_id == MeetingParticipant.user_id)
            .filter(Meeting.workspace_id == meeting.workspace_id,
                    WorkspaceMember.workspace_id == meeting.workspace_id,
                    func.lower(MeetingParticipant.provider) == provider,
                    MeetingParticipant.provider_user_id == provider_user_id,
                    ((MeetingParticipant.identity_verified_by.is_not(None)) |
                     (MeetingParticipant.email_verified.is_(True))),
                    MeetingParticipant.user_id.is_not(None))
            .distinct().all()
        )
        ids = {row[0] for row in matches}
        if len(ids) == 1:
            return IdentityResolution(next(iter(ids)), 0.99, "provider_user_id")
        if len(ids) > 1:
            return IdentityResolution()
    if email and email_verified:
        members = (
            db.query(User.id)
            .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
            .filter(WorkspaceMember.workspace_id == meeting.workspace_id,
                    func.lower(User.email) == email, User.email_verified.is_(True))
            .all()
        )
        ids = {row[0] for row in members}
        if len(ids) == 1:
            return IdentityResolution(next(iter(ids)), 0.98, "verified_email")
    return IdentityResolution()


def record_provider_participant(
    db: Session, meeting: Meeting, *, provider: str,
    provider_user_id: str | None, email: str | None,
    email_verified: bool, display_name: str | None,
) -> MeetingParticipant:
    resolution = resolve_provider_identity(
        db, meeting, provider=provider, provider_user_id=provider_user_id,
        email=email, email_verified=email_verified,
    )
    user_id = resolution.user_id if resolution.confidence >= APP_CONFIG.pilot.identity_confidence_threshold else None
    participant = (
        db.query(MeetingParticipant)
        .filter(MeetingParticipant.meeting_id == meeting.id,
                MeetingParticipant.provider == provider,
                MeetingParticipant.provider_user_id == provider_user_id)
        .first()
        if provider_user_id else None
    )
    if participant is None and email and email_verified:
        participant = db.query(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting.id,
            MeetingParticipant.provider == provider,
            func.lower(MeetingParticipant.provider_email) == email,
        ).first()
    if participant is None:
        participant = MeetingParticipant(meeting_id=meeting.id, name=(display_name or "Unknown participant")[:255])
        db.add(participant)
    participant.provider = provider
    participant.provider_user_id = provider_user_id
    participant.provider_email = email
    participant.email_verified = email_verified
    participant.identity_confidence = resolution.confidence if user_id else None
    participant.user_id = user_id
    if display_name:
        participant.name = display_name[:255]
    db.flush()
    return participant


def map_speaker_to_user(
    db: Session, meeting: Meeting, speaker_id: str,
    resolution: IdentityResolution,
) -> MeetingSpeakerMap | None:
    """Never infer an identity from Speaker 1 or a display name alone."""
    if not speaker_id or not resolution.user_id or resolution.confidence < APP_CONFIG.pilot.identity_confidence_threshold:
        return None
    if db.get(WorkspaceMember, (meeting.workspace_id, resolution.user_id)) is None:
        return None
    existing = db.query(MeetingSpeakerMap).filter(
        MeetingSpeakerMap.meeting_id == meeting.id,
        MeetingSpeakerMap.speaker_id == speaker_id,
    ).first()
    if existing and existing.user_id != resolution.user_id:
        return None
    if existing:
        return existing
    mapped = MeetingSpeakerMap(
        meeting_id=meeting.id, speaker_id=speaker_id,
        user_id=resolution.user_id, confidence=resolution.confidence,
        evidence=resolution.evidence,
    )
    db.add(mapped)
    db.flush()
    return mapped
