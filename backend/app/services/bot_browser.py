"""Workspace-scoped persistent Chromium sessions and shared launch settings."""

import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path


def profile_path(workspace_id: uuid.UUID, platform: str) -> Path:
    if platform not in {"google_meet", "teams", "zoom", "jitsi"}:
        raise ValueError("Unknown bot platform")
    return Path(os.getenv("PILOT_BOT_PROFILE_DIR", "/app/bot_profiles")) / str(uuid.UUID(str(workspace_id))) / platform


@contextmanager
def locked_profile(folder: Path):
    """Keep account setup and concurrent workers out of the same profile."""
    import fcntl
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(folder, 0o700)
    with (folder / ".meetpilot.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("This workspace bot browser is in use. Stop its meeting or account setup first.") from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def browser_options() -> dict:
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("Native bot display is unavailable. Run the meeting_bot service, which starts Xvfb and the window manager.")
    return {
        "executable_path": os.getenv("PILOT_CHROMIUM_PATH", "/usr/bin/chromium"),
        "headless": False,
        "ignore_default_args": ["--enable-automation"],
        "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                 "--disable-blink-features=AutomationControlled",
                 "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                 "--autoplay-policy=no-user-gesture-required", "--lang=en-US",
                 "--window-position=0,0", "--window-size=1366,900", "--password-store=basic"],
        "permissions": ["microphone", "camera"], "no_viewport": True,
        "locale": "en-US", "timezone_id": os.getenv("PILOT_BOT_TIMEZONE", "Asia/Kolkata"),
        "bypass_csp": True,
    }


async def import_auth_state(context, folder: Path, workspace_id: uuid.UUID) -> None:
    """Import desktop cookie state once; preserve refreshed persistent cookies."""
    local_state = folder / ".auth-state.json"
    if local_state.is_file():
        state = json.loads(local_state.read_text())
        await context.add_cookies(state.get("cookies", []))
    source = Path(os.getenv("PILOT_BOT_AUTH_DIR", "/app/bot_auth")) / f"{workspace_id}.json"
    stamp = folder / ".auth-imported"
    if not source.is_file():
        return
    revision = str(source.stat().st_mtime_ns)
    if stamp.is_file() and stamp.read_text() == revision:
        return
    state = json.loads(source.read_text())
    cookies = state.get("cookies", [])
    if cookies:
        await context.add_cookies(cookies)
    # Google's login is cookie-based. Import localStorage too for other providers.
    origins = state.get("origins", [])
    if origins:
        await context.add_init_script("""(() => {
          const origins = %s;
          const state = origins.find(item => item.origin === location.origin);
          for (const item of state?.localStorage || []) localStorage.setItem(item.name, item.value);
        })();""" % json.dumps(origins))
    stamp.write_text(revision)
    os.chmod(stamp, 0o600)


async def has_google_session(context) -> bool:
    cookies = await context.cookies(["https://accounts.google.com/", "https://meet.google.com/"])
    return any(item["name"] in {"SID", "__Secure-1PSID", "__Secure-3PSID"} for item in cookies)


async def save_auth_state(context, folder: Path) -> None:
    # Session-only Google cookies can be discarded by Chromium on exit. Store
    # them before closing, then restore through the Playwright cookie API.
    temporary = folder / ".auth-state.tmp"
    await context.storage_state(path=str(temporary))
    os.chmod(temporary, 0o600)
    temporary.replace(folder / ".auth-state.json")
