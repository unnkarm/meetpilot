"""Non-secret, bounded live-capture tuning for the upstream Vexa bot."""
import math
from pathlib import Path
from typing import Mapping


# Short isolated wakes must reach Whisper without waiting on the upstream
# 15-second idle timer. Keep LocalAgreement's two-pass confirmation minimum.
CAPTURE_DEFAULTS = {
    "BOT_SPEAKER_MIN_AUDIO_SEC": 0.4,
    "BOT_SPEAKER_SUBMIT_INTERVAL_SEC": 1.0,
    "BOT_SPEAKER_IDLE_TIMEOUT_SEC": 1.5,
    "BOT_SPEAKER_CONFIRM_THRESHOLD": 2,
    "BOT_SPEAKER_MAX_BUFFER_SEC": 30.0,
}
CAPTURE_BOUNDS = {
    "BOT_SPEAKER_MIN_AUDIO_SEC": (0.2, 2.0),
    "BOT_SPEAKER_SUBMIT_INTERVAL_SEC": (0.5, 3.0),
    "BOT_SPEAKER_IDLE_TIMEOUT_SEC": (0.8, 5.0),
    "BOT_SPEAKER_CONFIRM_THRESHOLD": (2, 4),
    "BOT_SPEAKER_MAX_BUFFER_SEC": (5.0, 60.0),
}


def capture_tuning(runtime_env: Mapping[str, str], file_env: Mapping[str, str] | None = None):
    """Return valid env values and warnings; never copy arbitrary env or secrets."""
    file_env = file_env or {}
    result, warnings = {}, []
    for name, default in CAPTURE_DEFAULTS.items():
        raw = (runtime_env.get(name) or "").strip() or (file_env.get(name) or "").strip()
        value = float(default)
        if raw:
            try:
                requested = float(raw)
                minimum, maximum = CAPTURE_BOUNDS[name]
                valid = math.isfinite(requested) and minimum <= requested <= maximum
                if name == "BOT_SPEAKER_CONFIRM_THRESHOLD":
                    valid = valid and requested.is_integer()
                if not valid:
                    raise ValueError("Out of range")
                value = requested
            except (TypeError, ValueError):
                warnings.append(f"{name} is invalid or outside its supported bounds; using {default}.")
        result[name] = str(int(value)) if name == "BOT_SPEAKER_CONFIRM_THRESHOLD" else str(value)
    return result, warnings


def build_advertises_capture_tuning(bot_root: str | Path) -> bool:
    """Inspect the actual image build rather than assuming vendored source parity."""
    root = Path(bot_root)
    source = ""
    for relative in ("dist/config.js", "dist/index.js"):
        try:
            path = root / relative
            # Both are small compiled modules; cap reads if an image differs.
            with path.open(encoding="utf-8") as stream:
                source += stream.read(1_000_000)
        except (OSError, UnicodeError):
            continue
    return all(name in source for name in CAPTURE_DEFAULTS)


def configure_capture_environment(runtime_env, file_env, bot_root, report=print):
    tuning, warnings = capture_tuning(runtime_env, file_env)
    for warning in warnings:
        report(f"[MeetPilot] Capture configuration: {warning}")
    supported = build_advertises_capture_tuning(bot_root)
    runtime_env.update(tuning)
    report("[MeetPilot] Requested meeting capture tuning: " + ", ".join(
        f"{name}={value}" for name, value in tuning.items()))
    if not supported:
        report("[MeetPilot] WARNING: this Vexa image does not advertise the speaker-stream tuning knobs. "
               "The requested values are passed through, but lower live-call latency is not verified. "
               "Check the image's bot build and the 'speaker-stream tuning enabled' runtime log.")
    return supported
