from typing import Any, TypedDict

from app.services.gemini_client import generate_json

_COMBINED_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "key_takeaways": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "assignee_name": {"type": "string"},
                    "due_date": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "transcript_timestamp": {"type": "string"},
                },
                "required": ["title", "priority"],
            },
        },
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "outcome": {"type": "string"},
                    "transcript_timestamp": {"type": "string"},
                },
                "required": ["topic", "outcome"],
            },
        },
    },
    "required": ["overview", "key_takeaways", "next_steps", "tasks", "decisions"],
}

_SYSTEM_INSTRUCTION = (
    "You are an expert meeting intelligence assistant. Given a timestamped meeting transcript, "
    "produce a complete executive analysis in one step:\n"
    "1. overview: 2-4 sentence executive summary of key topics and outcomes.\n"
    "2. key_takeaways: 3-5 concise bullet points (one sentence each).\n"
    "3. next_steps: 2-5 actionable bullet points.\n"
    "4. tasks: Concrete action items with imperative title, assignee_name (if mentioned), "
    "due_date (e.g. 'This Friday' or 'End of Week'), priority (low/medium/high), and transcript_timestamp (mm:ss).\n"
    "5. decisions: Agreed consensus items with topic, outcome, and transcript_timestamp (mm:ss).\n"
    "Be concise, accurate, and avoid inventing details not present in the transcript."
)


class MeetingInsightsDict(TypedDict):
    overview: str
    key_takeaways: list[str]
    next_steps: list[str]
    tasks: list[dict[str, Any]]
    decisions: list[dict[str, Any]]


def generate_meeting_insights(transcript_text: str, participant_names: list[str] | None = None) -> MeetingInsightsDict:
    """Generates summary, action items, and decisions in a single LLM pass to save tokens and avoid rate limits."""
    participants_hint = ", ".join(participant_names) if participant_names else "Team"
    result = generate_json(
        prompt=f"Meeting participants: {participants_hint}\n\nMeeting transcript:\n\n{transcript_text}",
        response_schema=_COMBINED_SCHEMA,
        system_instruction=_SYSTEM_INSTRUCTION,
    )
    return {
        "overview": result.get("overview", ""),
        "key_takeaways": result.get("key_takeaways", []),
        "next_steps": result.get("next_steps", []),
        "tasks": result.get("tasks", []),
        "decisions": result.get("decisions", []),
    }


def generate_summary(transcript_text: str) -> dict[str, Any]:
    insights = generate_meeting_insights(transcript_text)
    return {
        "overview": insights["overview"],
        "key_takeaways": insights["key_takeaways"],
        "next_steps": insights["next_steps"],
    }
