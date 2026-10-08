"""Save a workspace-specific Google sign-in state for the local meeting bot.

Run this on the operator's desktop, never in a headless Docker container.
The operator signs in directly to Google in a visible local Chrome window.
"""

import argparse
import os
import json
import subprocess
import sys
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright


def container_setup(workspace_id):
    """Use the exact Linux Chromium profile the worker will use next time."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services.bot_browser import browser_options, locked_profile, profile_path
    os.environ.update(json.loads(Path("/tmp/meetpilot-display.json").read_text()))
    folder = profile_path(workspace_id, "google_meet")
    helpers = []
    with locked_profile(folder), sync_playwright() as playwright:
        try:
            helpers.append(subprocess.Popen(["x11vnc", "-display", os.environ["DISPLAY"],
                                             "-auth", os.environ["XAUTHORITY"], "-localhost",
                                             "-rfbport", "5900", "-nopw", "-forever", "-shared", "-quiet"]))
            helpers.append(subprocess.Popen(["websockify", "--web=/usr/share/novnc/", "6080", "localhost:5900"]))
            context = playwright.chromium.launch_persistent_context(str(folder), **browser_options())
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://accounts.google.com/", wait_until="domcontentloaded")
                print("Open http://localhost:6080/vnc.html to sign in directly to Google.", flush=True)
                print("Use the bot account invited by the host. No credentials are sent to MeetPilot.", flush=True)
                input("After completing sign-in in that browser, press Enter here: ")
                page.goto("https://myaccount.google.com/", wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                cookies = context.cookies("https://accounts.google.com/")
                if "accounts.google.com" in page.url or not any(c["name"] in {"SID", "__Secure-1PSID", "__Secure-3PSID"} for c in cookies):
                    raise RuntimeError("Google sign-in is incomplete. Finish sign-in before retrying setup.")
                temporary = folder / ".auth-state.tmp"
                context.storage_state(path=str(temporary))
                os.chmod(temporary, 0o600)
                temporary.replace(folder / ".auth-state.json")
                # Do not allow an older desktop cookie export to replace this login.
                exported = Path(os.getenv("PILOT_BOT_AUTH_DIR", "/app/bot_auth")) / f"{workspace_id}.json"
                if exported.is_file():
                    (folder / ".auth-imported").write_text(str(exported.stat().st_mtime_ns))
                print(f"Persistent bot session saved for workspace {workspace_id}.", flush=True)
            finally:
                context.close()
        finally:
            for helper in reversed(helpers):
                helper.terminate()
                try:
                    helper.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    helper.kill()
                    helper.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare local MeetPilot bot sign-in state")
    parser.add_argument("workspace_id", type=uuid.UUID)
    parser.add_argument("--container", action="store_true", help="Sign in through the local bot browser console using its persistent Linux profile")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "bot_auth")
    args = parser.parse_args()
    if args.container:
        container_setup(args.workspace_id)
        return
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{args.workspace_id}.json"
    temporary = output_dir / f"{args.workspace_id}.json.tmp"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome", headless=False,
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://accounts.google.com/", wait_until="domcontentloaded")
            print("Sign in to the Google account invited to this workspace's meetings.")
            input("When sign-in is complete, press Enter here to save this workspace's bot state: ")
            page.goto("https://myaccount.google.com/", wait_until="domcontentloaded")
            if "accounts.google.com" in page.url:
                raise RuntimeError("Google sign-in is incomplete; no bot state was saved")
            context.storage_state(path=str(temporary))
            os.chmod(temporary, 0o600)
            temporary.replace(destination)
            print(f"Saved bot sign-in state for workspace {args.workspace_id}: {destination}")
            print("Keep this file private. It grants access to the bot Google account.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
