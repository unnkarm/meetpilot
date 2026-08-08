import json
import logging
import uuid
import httpx
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret
from app.models.decision import Decision
from app.models.integration import WorkspaceIntegration
from app.models.meeting import Meeting
from app.models.task import Task

logger = logging.getLogger(__name__)


def post_meeting_digest_to_discord(db: Session, meeting_id: uuid.UUID) -> bool:
    """Posts a rich executive digest to the workspace's configured Discord channel upon meeting completion."""
    try:
        meeting = db.get(Meeting, meeting_id)
        if not meeting:
            return False

        integration = (
            db.query(WorkspaceIntegration)
            .filter(
                WorkspaceIntegration.workspace_id == meeting.workspace_id,
                WorkspaceIntegration.provider == "discord",
                WorkspaceIntegration.is_connected == True,
            )
            .first()
        )
        if not integration or not integration.encrypted_config:
            return False

        decrypted_raw = decrypt_secret(integration.encrypted_config)
        if not decrypted_raw:
            return False

        config = json.loads(decrypted_raw)
        webhook_url = config.get("webhook_url")
        if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
            return False

        # Gather summary, tasks, decisions
        duration_mins = int((meeting.duration_seconds or 0) // 60)
        duration_secs = int((meeting.duration_seconds or 0) % 60)
        duration_str = f"{duration_mins:02d}:{duration_secs:02d}"

        overview_text = "No summary available."
        key_takeaways = []
        if meeting.summary:
            overview_text = meeting.summary.overview or overview_text
            key_takeaways = meeting.summary.key_takeaways or []

        tasks = (
            db.query(Task)
            .filter(Task.meeting_id == meeting.id)
            .order_by(Task.created_at.asc())
            .limit(5)
            .all()
        )
        task_bullets = "\n".join(
            [f"• **{t.title}** ({t.assignee_name or 'Unassigned'} — *{t.priority.value.upper()}*)" for t in tasks]
        ) or "No pending action items extracted."

        decisions = (
            db.query(Decision)
            .filter(Decision.meeting_id == meeting.id)
            .limit(3)
            .all()
        )
        decision_bullets = "\n".join(
            [f"• **{d.topic}**: {d.outcome}" for d in decisions]
        ) or "No consensus decisions recorded."

        embed = {
            "title": f"🎙️ Meeting Digest: {meeting.title}",
            "description": overview_text[:1200],
            "color": 0x8B5CF6,  # MeetPilot Luxury Violet
            "fields": [
                {
                    "name": "⏱️ Meeting Details",
                    "value": f"**Duration:** {duration_str} | **Participants:** {len(meeting.participants)}",
                    "inline": True,
                },
                {
                    "name": "📋 Key Takeaways",
                    "value": "\n".join([f"• {k}" for k in key_takeaways[:3]]) or "None listed",
                    "inline": False,
                },
                {
                    "name": f"✅ Top Action Items ({len(tasks)})",
                    "value": task_bullets[:1000],
                    "inline": False,
                },
                {
                    "name": "🎯 Consensus Decisions",
                    "value": decision_bullets[:1000],
                    "inline": False,
                },
            ],
            "footer": {
                "text": "MeetPilot AI • Enterprise Meeting Intelligence",
            },
        }

        payload = {
            "username": "MeetPilot AI",
            "embeds": [embed],
        }

        response = httpx.post(webhook_url, json=payload, timeout=10.0)
        if response.status_code in (200, 204):
            logger.info(f"Successfully posted meeting digest to Discord for meeting {meeting_id}")
            return True
        else:
            logger.warning(f"Discord webhook returned status {response.status_code}: {response.text}")
            return False
    except Exception as exc:
        logger.error(f"Failed to post meeting digest to Discord: {exc}", exc_info=True)
        return False
