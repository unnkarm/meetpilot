"""Meeting-specific recognition hints and display preferences."""
from typing import Literal

MeetingLanguage = Literal["en", "hi", "bn", "ta", "te", "mr", "gu", "pa", "ur", "auto"]
DisplayScript = Literal["original", "romanized"]
LANGUAGES = {"en", "hi", "bn", "ta", "te", "mr", "gu", "pa", "ur", "auto"}


def recognition_hint(language: str | None) -> str | None:
    if language is None or language == "auto":
        return None
    if language not in LANGUAGES:
        raise ValueError("Unsupported meeting language")
    return language


def display_script(language: str | None, requested: str | None = None) -> str:
    result = requested or ("romanized" if language in {"hi", "bn"} else "original")
    if result not in {"original", "romanized"}:
        raise ValueError("Unsupported display script")
    if result == "romanized" and language not in {"hi", "bn", "auto", None}:
        raise ValueError("Romanized display is available for Hindi and Bengali")
    return result
