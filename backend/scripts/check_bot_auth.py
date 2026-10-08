"""Verify a saved bot session after reopening Chromium without printing secrets."""
import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.async_api import async_playwright
from app.services.bot_browser import browser_options, has_google_session, import_auth_state, locked_profile, profile_path, save_auth_state


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace_id", type=uuid.UUID)
    args = parser.parse_args()
    os.environ.update(json.loads(Path("/tmp/meetpilot-display.json").read_text()))
    folder = profile_path(args.workspace_id, "google_meet")
    with locked_profile(folder):
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(str(folder), **browser_options())
            try:
                await import_auth_state(context, folder, args.workspace_id)
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto("https://myaccount.google.com/", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                if "accounts.google.com" in page.url or not await has_google_session(context):
                    raise RuntimeError("Saved bot account is signed out after browser reopen")
                await save_auth_state(context, folder)
                print("google_session_after_browser_reopen=ok", flush=True)
            finally:
                await context.close()


if __name__ == "__main__":
    asyncio.run(main())
