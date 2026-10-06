from datetime import date
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.app_config import APP_CONFIG
from app.services.ai_provider import get_ai_provider

SUMMARY_PROMPT_VERSION = APP_CONFIG.language.prompt_version
TASK_EXTRACTION_PROMPT_VERSION = APP_CONFIG.language.prompt_version
DECISION_EXTRACTION_PROMPT_VERSION = APP_CONFIG.language.prompt_version

_SYSTEM_INSTRUCTION = (
    f"Prompt version: {SUMMARY_PROMPT_VERSION}. You are an expert multilingual meeting intelligence assistant. "
    "Read the original timestamped transcript without translating it first. Preserve the meaning, "
    "people's names, company and product names, URLs, APIs, and technical identifiers. "
    "Keep JSON field names and priority enum values in English; write natural-language values "
    "in the requested meeting language. Do not convert code-switched technical terms. "
    "Produce a complete executive analysis in one step:\n"
    "1. decisions: Every explicit agreement or choice, including statements equivalent to "
    "'we decided' in any language, with topic, outcome, transcript_timestamp (mm:ss), "
    "and source_quote. A decision is not a task unless someone separately commits to an action.\n"
    "2. tasks: Only concrete future actions someone commits to doing; do not turn agreed "
    "technology choices or general discussion into tasks. Include imperative title, assignee_name (if mentioned), "
    "due_date (ISO YYYY-MM-DD only when an absolute or unambiguous relative date is spoken; otherwise null), "
    "priority (low/medium/high), transcript_timestamp (mm:ss), and source_quote (an exact excerpt from that speech turn).\n"
    "3. overview: 2-4 sentence executive summary of key topics and outcomes.\n"
    "4. key_takeaways: 3-5 concise points.\n"
    "5. next_steps: 2-5 actionable points.\n"
    "6. objectives, blockers, follow_ups: concise grounded points. Each point has text, "
    "transcript_timestamp (mm:ss), and an exact source_quote. Omit unsupported points.\n"
    "Copy source_quote verbatim from the original text AFTER the speaker label and colon; "
    "never include the speaker label, timestamp, or a paraphrase in source_quote. "
    "Suggestions and questions are not decisions.\n"
    "Be concise, accurate, and never invent details, assignees, dates, or evidence."
)


class ExtractedTask(BaseModel):
    title: str = Field(min_length=3)
    assignee_name: str | None = None
    due_date: str | None = None
    priority: str = "medium"
    transcript_timestamp: str
    source_quote: str | None = None

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str) -> str:
        if value not in {"low", "medium", "high"}:
            raise ValueError("invalid priority")
        return value

    @field_validator("due_date", mode="before")
    @classmethod
    def valid_date(cls, value: str | None) -> str | None:
        if isinstance(value, str) and value.strip().casefold() in {"", "null", "none", "unknown"}:
            return None
        if value:
            date.fromisoformat(value)
        return value


class ExtractedDecision(BaseModel):
    topic: str = Field(min_length=3)
    outcome: str = Field(min_length=3)
    transcript_timestamp: str
    source_quote: str | None = None


class GroundedExecutivePoint(BaseModel):
    text: str = Field(min_length=3)
    transcript_timestamp: str
    source_quote: str


class MeetingInsights(BaseModel):
    decisions: list[ExtractedDecision]
    tasks: list[ExtractedTask]
    overview: str = Field(min_length=3)
    key_takeaways: list[str]
    next_steps: list[str]
    objectives: list[GroundedExecutivePoint] = Field(default_factory=list)
    blockers: list[GroundedExecutivePoint] = Field(default_factory=list)
    follow_ups: list[GroundedExecutivePoint] = Field(default_factory=list)


class SummaryOnly(BaseModel):
    overview: str = Field(min_length=3)
    key_takeaways: list[str]
    next_steps: list[str]


def _transcript_windows(text: str, limit: int) -> list[str]:
    """Keep complete timestamped turns together within the model context budget."""
    windows: list[str] = []
    current = ""
    for line in text.splitlines():
        if current and len(current) + len(line) + 1 > limit:
            windows.append(current)
            current = ""
        if len(line) > limit:
            raise ValueError("Transcript turn exceeds configured AI context limit")
        current += line + "\n"
    if current:
        windows.append(current)
    return windows


def _dedupe_items(items: list[dict], field: str) -> list[dict]:
    """Merge repeated interpretations of the same action or decision."""
    chosen: dict[tuple[str, str], dict] = {}
    for item in items:
        title = " ".join(item[field].casefold().split())
        assignee = " ".join((item.get("assignee_name") or "").casefold().split())
        key = (title, assignee)
        if assignee and (title, "") in chosen:
            chosen.pop((title, ""))
        elif not assignee and any(existing_title == title and existing_assignee for existing_title, existing_assignee in chosen):
            continue
        previous = chosen.get(key)
        if previous is None or (
            bool(item.get("assignee_name")), bool(item.get("due_date")), len(item.get("source_quote") or "")
        ) > (
            bool(previous.get("assignee_name")), bool(previous.get("due_date")), len(previous.get("source_quote") or "")
        ):
            chosen[key] = item
    return list(chosen.values())


def generate_meeting_insights(
    transcript_text: str,
    participant_names: list[str] | None = None,
    language_code: str | None = None,
    language_name: str | None = None,
    meeting_date: date | None = None,
) -> dict[str, Any]:
    """Generate schema-validated intelligence using the active provider."""
    participants_hint = ", ".join(participant_names) if participant_names else "Team"
    provider = get_ai_provider()
    windows = _transcript_windows(transcript_text, APP_CONFIG.rag.max_context_chars)
    if not windows:
        raise ValueError("Empty meeting transcript")
    output_language = (
        language_name or language_code
        if APP_CONFIG.language.summary_language_mode == "meeting"
        else None
    )
    language_instruction = (
        f"Use {output_language} for natural-language output fields."
        if output_language else
        "Language confidence is low; use the dominant language evident in the transcript without forcing English."
    )
    date_context = f"Meeting date: {meeting_date.isoformat()}." if meeting_date else "Meeting date is unknown."
    protected_terms = list(dict.fromkeys(
        term for term in re.findall(r"\b[A-Za-z][A-Za-z0-9_./:-]*\b", transcript_text)
        if len(term) > 2 and (any(char.isupper() for char in term[1:]) or any(char.isdigit() for char in term))
    ))[:30]
    terminology_instruction = (
        "Copy these exact spellings when mentioned, without transliteration: " + ", ".join(protected_terms) + "."
        if protected_terms else ""
    )
    parts = [provider.structured(
        prompt=f"{language_instruction}\n{date_context}\n{terminology_instruction}\nKnown participants: {participants_hint}\n"
               "Resolve relative dates only if unambiguous from this meeting date; otherwise null. "
               "Every task, decision, objective, blocker, and follow-up must cite the exact transcript timestamp "
               "and quote its original-language evidence. "
               f"Only agreed decisions count.\n\nMeeting transcript:\n\n{window}",
        schema=MeetingInsights,
        system=_SYSTEM_INSTRUCTION,
    ) for window in windows]
    if len(parts) == 1:
        result = parts[0].model_dump()
        result["tasks"] = _dedupe_items(result["tasks"], "title")
        result["decisions"] = _dedupe_items(result["decisions"], "topic")
        return result

    digest = "\n".join(f"Part {index + 1}: {part.overview}\nTakeaways: {'; '.join(part.key_takeaways)}\nNext steps: {'; '.join(part.next_steps)}"
                       for index, part in enumerate(parts))
    summary = provider.structured(
        f"{language_instruction}\nCombine these partial meeting summaries without adding new facts:\n" + digest,
        SummaryOnly,
        system=f"Prompt version: {SUMMARY_PROMPT_VERSION}. Return one concise overview, key takeaways and next steps "
               "in the same requested language, grounded only in the supplied partial summaries. "
               "Preserve proper nouns and technical terms.",
    )
    tasks = _dedupe_items([task.model_dump() for part in parts for task in part.tasks], "title")
    decisions = _dedupe_items([decision.model_dump() for part in parts for decision in part.decisions], "topic")
    sections = {
        name: _dedupe_items([point.model_dump() for part in parts for point in getattr(part, name)], "text")
        for name in ("objectives", "blockers", "follow_ups")
    }
    return {**summary.model_dump(), "tasks": tasks, "decisions": decisions, **sections}


def generate_summary(transcript_text: str) -> dict[str, Any]:
    insights = generate_meeting_insights(transcript_text)
    return {
        "overview": insights["overview"],
        "key_takeaways": insights["key_takeaways"],
        "next_steps": insights["next_steps"],
    }
