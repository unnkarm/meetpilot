from typing import TypedDict

from app.services.gemini_client import generate_json

_SCHEMA = {
    "type": "object",
    "properties": {
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
    "required": ["tasks", "decisions"],
}

_SYSTEM_INSTRUCTION = (
    "You extract structured action items and decisions from meeting transcripts. "
    "For each concrete action item mentioned, output a task with a clear imperative title, "
    "the assignee_name (use the participant's actual name if the transcript makes ownership "
    "clear, otherwise omit it), a due_date in the phrasing used in the transcript (e.g. "
    "'This Friday'), a priority estimate (low/medium/high) based on urgency language, and the "
    "transcript_timestamp (mm:ss) where it was discussed. For each explicit decision or "
    "consensus reached, output a decision with a short topic, the outcome that was agreed, and "
    "its transcript_timestamp. Only include items clearly present in the transcript -- do not "
    "invent tasks or decisions."
)


class ExtractedTaskDict(TypedDict, total=False):
    title: str
    assignee_name: str
    due_date: str
    priority: str
    transcript_timestamp: str


class ExtractedDecisionDict(TypedDict, total=False):
    topic: str
    outcome: str
    transcript_timestamp: str


def extract_tasks_and_decisions(
    transcript_text: str, participant_names: list[str]
) -> tuple[list[ExtractedTaskDict], list[ExtractedDecisionDict]]:
    participants_hint = ", ".join(participant_names) if participant_names else "unknown"
    result = generate_json(
        prompt=(
            f"Meeting participants: {participants_hint}\n\n"
            f"Meeting transcript:\n\n{transcript_text}"
        ),
        response_schema=_SCHEMA,
        system_instruction=_SYSTEM_INSTRUCTION,
    )
    return result.get("tasks", []), result.get("decisions", [])
