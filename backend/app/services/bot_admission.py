"""Explicit browser admission states, based on Vexa's bounded admission flow.

Only named join controls are actionable. Structural Google selectors are useful
for diagnostics, but are never evidence that an arbitrary button submits a join.
"""

from enum import Enum


class JoinState(str, Enum):
    LOADING = "loading"
    PREJOIN = "prejoin"
    WAITING = "waiting_for_host"
    ADMITTED = "admitted"
    AUTH_REQUIRED = "account_required"
    CHALLENGE = "human_verification_required"
    DENIED = "host_denied"
    BLOCKED = "access_blocked"
    ENDED = "ended_or_invalid"
    REDIRECTED = "redirected"


WAITING_COPY = (
    "asking to be let in", "you'll join the call when someone lets you",
    "waiting for the host", "someone will let you in", "you're in the waiting room",
    "please wait until a meeting host brings you into the call",
    "someone in the meeting should let you in soon", "waiting for someone to let you in",
    "the host will let you in soon", "wait for the host to start this meeting",
    "please wait, the meeting host will let you in soon",
)
DENIED_COPY = (
    "denied your request", "request to join was denied", "you were denied",
    "weren't allowed to join", "not admitted", "ask to join again",
)
BLOCKED_COPY = (
    "you can't join this video call", "you cannot join this video call",
    "you can't join this meeting", "you cannot join this meeting",
    "not allowed to join", "access denied",
)
JOIN_PATTERN = r"^\s*(?:Join now|Ask to join|Request to join|Join meeting|Join call|Join without an account|Join|Switch here)\s*$"


def classify_page(text: str, url: str, *, in_call: bool = False,
                  join_visible: bool = False, name_visible: bool = False,
                  challenge_visible: bool = False) -> JoinState:
    text = text.replace("’", "'").casefold()
    if any(copy in text for copy in DENIED_COPY):
        return JoinState.DENIED
    if challenge_visible:
        return JoinState.CHALLENGE
    if "accounts.google.com/" in url or "sign in to join" in text:
        return JoinState.AUTH_REQUIRED
    if any(copy in text for copy in BLOCKED_COPY):
        return JoinState.BLOCKED
    if any(copy in text for copy in ("meeting has ended", "meeting doesn't exist", "invalid meeting code")):
        return JoinState.ENDED
    if any(copy in text for copy in WAITING_COPY):
        return JoinState.WAITING
    if join_visible or name_visible or "what's your name?" in text:
        return JoinState.PREJOIN
    if in_call:
        return JoinState.ADMITTED
    if "workspace.google.com/products/meet" in url or url.rstrip("/") == "https://meet.google.com":
        return JoinState.REDIRECTED
    return JoinState.LOADING


ERROR_MESSAGES = {
    JoinState.AUTH_REQUIRED: "This meeting requires a Google account. Sign the bot into the account invited by the host using the workspace bot setup.",
    JoinState.DENIED: "The host denied the bot's request to join. Ask the host to allow the bot before retrying.",
    JoinState.BLOCKED: "The meeting provider blocked access. This can require an invited account or browser verification. Check the saved bot screenshot and the host's access settings.",
    JoinState.ENDED: "The meeting provider says the meeting ended or the code is invalid.",
    JoinState.REDIRECTED: "Google redirected the browser away from the meeting. Check the original link and account access; this does not prove the meeting ended.",
}
