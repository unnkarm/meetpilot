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
            # The spoken wake name stays English. ASR can write that name in
            # the surrounding sentence's script during code-switching.
            direct = r"(?:(?:hey|hi|hello|ok|okay)[\s,]+)?(?:meet[\s-]*)?(?:pilot|পাইলট|पायलट|पाइलट)"
        self.pattern = re.compile(r"(?<!\w)" + direct + r"\b[\s,.:!?-]*",
                                  re.IGNORECASE | re.UNICODE)

    def detect(self, text: str) -> str | None:
        match = self.pattern.search(text)
        return text[match.end():].strip() if match else None


class WakeGate:
    """Wake capture plus a short, speaker-bound conversational follow-up window."""
    capture_seconds = 10.0
    followup_seconds = 30.0
    def __init__(self, provider=None, clock=time.monotonic):
        self.provider = provider or get_wakeword_provider()
        self.clock = clock
        self.last_wake = -100.0
        self.consumed = []
        self.armed_until = 0.0
        self.speaker = None
        self.followup = False
        self.wake_utterance_id = None

    @staticmethod
    def normalize_speaker(speaker):
        if not isinstance(speaker, str) or not speaker.strip():
            return None
        speaker = speaker.strip()
        # Diarization labels identify a track, not a participant. Do not use
        # them to hand an open conversation to another person in the call.
        if re.fullmatch(r"(?:speaker[\s_-]*\d*|s\d+|unknown(?: speaker)?)", speaker, re.I):
            return None
        return speaker.casefold()

    def observe(self, text, *, final=False, utterance_id=None, speaker=None, confidence=None):
        speaker = self.normalize_speaker(speaker)
        query = self.provider.detect(text)
        # Provider labels can become available between a partial and its final.
        # The stable utterance identity still represents the same wake.
        identity = utterance_id if utterance_id else None
        if query is None:
            return False
        if identity and identity in self.consumed:
            if identity == self.wake_utterance_id and self.speaker is None and speaker is not None:
                self.speaker = speaker
            return False
        now = self.clock()
        # Stable utterance IDs deduplicate partial/final updates. A global
        # cooldown used to discard the next genuine request after "Pilot".
        if identity is None and now - self.last_wake < 0.35:
            return False
        self.last_wake = now
        self.armed_until = now + self.capture_seconds
        self.speaker = speaker
        self.followup = False
        self.wake_utterance_id = identity
        if identity:
            self.consumed = (self.consumed + [identity])[-64:]
        return True

    def accepts(self, speaker=None):
        speaker = self.normalize_speaker(speaker)
        return 0 < self.armed_until and self.clock() <= self.armed_until and (not self.speaker or speaker == self.speaker)

    def extend_capture(self):
        if not self.followup:
            self.armed_until = self.clock() + self.capture_seconds

    def open_followup(self, speaker=None, *, allow_unlabelled=False):
        speaker = self.normalize_speaker(speaker)
        if speaker is None and not allow_unlabelled:
            self.disarm()
            return
        self.speaker = speaker
        self.followup = True
        self.armed_until = self.clock() + self.followup_seconds

    def arm_interrupt(self, speaker=None):
        self.speaker = self.normalize_speaker(speaker)
        self.followup = False
        self.armed_until = self.clock() + self.capture_seconds

    def disarm(self):
        self.armed_until = 0.0
        self.speaker = None
        self.followup = False


def get_wakeword_provider() -> WakeWordProvider:
    if APP_CONFIG.pilot.wakeword_provider == "transcript_phrase":
        return TranscriptPhraseWakeWord()
    raise RuntimeError("Unsupported Pilot wake-word provider")
