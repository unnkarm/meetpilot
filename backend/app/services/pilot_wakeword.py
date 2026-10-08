"""Responsive name recognition on partial and final local transcripts."""

import re
import time
from abc import ABC, abstractmethod

from app.core.app_config import APP_CONFIG


class WakeWordProvider(ABC):
    @abstractmethod
    def detect(self, text: str) -> str | None:
        """Return the spoken query after the wake phrase, or None."""
        raise NotImplementedError


class TranscriptPhraseWakeWord(WakeWordProvider):
    def __init__(self, phrase: str | None = None):
        phrase = phrase or APP_CONFIG.pilot.wake_word
        direct = r"[\s,]+".join(map(re.escape, phrase.split()))
        if phrase.lower() == "hey pilot":
            direct = r"(?:(?:hey|hi|hello|ok|okay)[\s,]+)?(?:meet[\s-]*)?pilot"
        self.pattern = re.compile(r"(?<!\w)" + direct + r"\b[\s,.:!?-]*",
                                  re.IGNORECASE | re.UNICODE)

    def detect(self, text: str) -> str | None:
        match = self.pattern.search(text)
        return text[match.end():].strip() if match else None


class WakeGate:
    """Responsive name recognition with one acknowledgement per utterance."""
    def __init__(self, provider=None, clock=time.monotonic):
        self.provider = provider or get_wakeword_provider()
        self.clock = clock
        self.last_wake = -100.0
        self.consumed = []
        self.armed_until = 0.0
        self.speaker = None

    def observe(self, text, *, final=False, utterance_id=None, speaker=None, confidence=None):
        if speaker and (speaker.lower().startswith("speaker") or speaker.lower() == "unknown speaker"):
            speaker = None
        query = self.provider.detect(text)
        identity = (utterance_id, speaker) if utterance_id else None
        if query is None:
            return False
        if identity and identity in self.consumed:
            return False
        now = self.clock()
        if now - self.last_wake < 3.0:
            return False
        self.last_wake = now
        self.armed_until = now + 10.0
        self.speaker = speaker
        if identity:
            self.consumed = (self.consumed + [identity])[-64:]
        return True

    def accepts(self, speaker=None):
        if speaker and (speaker.lower().startswith("speaker") or speaker.lower() == "unknown speaker"):
            speaker = None
        return self.clock() <= self.armed_until and (not self.speaker or speaker == self.speaker)

    def disarm(self):
        self.armed_until = 0.0
        self.speaker = None


def get_wakeword_provider() -> WakeWordProvider:
    if APP_CONFIG.pilot.wakeword_provider == "transcript_phrase":
        return TranscriptPhraseWakeWord()
    raise RuntimeError("Unsupported Pilot wake-word provider")
