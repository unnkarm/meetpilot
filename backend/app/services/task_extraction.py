"""Compatibility wrapper around the shared multilingual intelligence pass."""

from typing import TypedDict

from app.services.meeting_analysis import generate_meeting_insights


class ExtractedTaskDict(TypedDict, total=False):
    title: str
    assignee_name: str
    due_date: str
    priority: str
    transcript_timestamp: str
    source_quote: str


class ExtractedDecisionDict(TypedDict, total=False):
    topic: str
    outcome: str
    transcript_timestamp: str
    source_quote: str


def extract_tasks_and_decisions(
    transcript_text: str, participant_names: list[str], language_code: str | None = None,
) -> tuple[list[ExtractedTaskDict], list[ExtractedDecisionDict]]:
    result = generate_meeting_insights(transcript_text, participant_names, language_code)
    return result.get("tasks", []), result.get("decisions", [])
