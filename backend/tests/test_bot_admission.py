"""Admission regressions, including Chromium DOM transitions when enabled."""
import os
import unittest
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services.bot_admission import JoinState, classify_page
from app.services.native_meeting import MeetingTarget, parse_meeting_target
from app.workers.meeting_bot import MeetingJoinError, _join
from app.services.bot_browser import has_google_session, import_auth_state, save_auth_state, locked_profile


class AdmissionTests(unittest.TestCase):
    def test_google_lobby_message_is_waiting_not_admitted(self):
        self.assertEqual(classify_page("You'll join the call when someone lets you in", "https://meet.google.com/abc-defg-hij", in_call=True), JoinState.WAITING)

    def test_denial_wins_over_challenge(self):
        self.assertEqual(classify_page("The host denied your request", "https://meet.google.com/abc-defg-hij", challenge_visible=True), JoinState.DENIED)

    def test_home_redirect_is_not_evidence_meeting_ended(self):
        self.assertEqual(classify_page("Video meetings", "https://workspace.google.com/products/meet/"), JoinState.REDIRECTED)

    def test_prejoin_preview_does_not_confirm_admission(self):
        self.assertEqual(classify_page("What's your name?", "https://meet.google.com/abc-defg-hij", in_call=True), JoinState.PREJOIN)

    def test_keep_zoom_passcode_and_teams_tenant_context(self):
        zoom = "https://us02web.zoom.us/j/123456789?pwd=secret&uname=Test"
        teams = "https://teams.microsoft.com/l/meetup-join/19%3ameeting/0?context=%7B%22Tid%22%3A%22tenant%22%7D"
        self.assertEqual(parse_meeting_target(zoom).url, zoom)
        self.assertEqual(parse_meeting_target(teams).url, teams)
        self.assertIn("hl=en", parse_meeting_target("meet.google.com/abc-defg-hij?hl=fr").url)

    def test_reject_unsafe_links_and_bad_google_code(self):
        for link in ("http://meet.google.com/abc-defg-hij", "https://user@meet.google.com/abc-defg-hij", "https://meet.google.com:444/abc-defg-hij", "https://meet.google.com.evil.test/abc-defg-hij", "https://meet.google.com/no-code"):
            with self.subTest(link=link), self.assertRaises(ValueError):
                parse_meeting_target(link)


@unittest.skipUnless(os.getenv("MEETPILOT_RUN_BROWSER_INTEGRATION") == "1", "Requires local Chromium")
class BrowserAdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        self.page = await self.browser.new_page()
        self.target = MeetingTarget("google_meet", "https://meet.google.com/abc-defg-hij", "abc-defg-hij")
        self.native_click = patch("app.workers.meeting_bot.native_input.click", new=AsyncMock(side_effect=RuntimeError("Headless fixture")))
        self.native_click.start()

    async def asyncTearDown(self):
        self.native_click.stop()
        await self.browser.close()
        await self.playwright.stop()

    async def fixture(self, html):
        await self.page.route(self.target.url, lambda route: route.fulfill(body=html, content_type="text/html"))

    async def test_lobby_never_clicks_return_home_and_later_admits(self):
        await self.fixture("""<body><p>You'll join the call when someone lets you in</p>
          <button jsname="x" onclick="window.homeClicked=true"><span>Return to home screen</span></button>
          <script>setTimeout(()=>document.body.innerHTML='<div data-self-name="Bot">Bot</div><button aria-label="Present now">Present now</button>',250)</script></body>""")
        states = []
        async def report(state): states.append(state)
        await _join(self.page, self.target, "MeetPilot AI Bot", on_state=report, prejoin_timeout=1, admission_timeout=2, poll_interval=0.05)
        self.assertIn(JoinState.WAITING, states)
        self.assertEqual(states[-1], JoinState.ADMITTED)
        self.assertIsNone(await self.page.evaluate("window.homeClicked"))

    async def test_join_is_clicked_once_with_delayed_lobby_update(self):
        await self.fixture("""<button onclick="window.clicks=(window.clicks||0)+1;setTimeout(()=>document.body.innerHTML='<p>You will wait</p><p>You\u2019ll join the call when someone lets you in</p>',300)">Ask to join</button>""")
        with self.assertRaises(MeetingJoinError) as caught:
            await _join(self.page, self.target, "MeetPilot AI Bot", prejoin_timeout=1, admission_timeout=0.6, poll_interval=0.05)
        self.assertEqual(caught.exception.code, "admission_timeout")
        self.assertEqual(await self.page.evaluate("window.clicks"), 1)

    async def test_unrelated_structural_button_is_never_clicked(self):
        await self.fixture('<button jsname="x" onclick="window.bad=true"><span>Return to home screen</span></button>')
        with self.assertRaises(MeetingJoinError) as caught:
            await _join(self.page, self.target, "Bot", prejoin_timeout=0.15, poll_interval=0.02)
        self.assertEqual(caught.exception.code, "prejoin_timeout")
        self.assertIsNone(await self.page.evaluate("window.bad"))

    async def test_host_denial_is_reported(self):
        await self.fixture('<p>The host denied your request to join.</p>')
        with self.assertRaises(MeetingJoinError) as caught:
            await _join(self.page, self.target, "Bot")
        self.assertEqual(caught.exception.code, "host_denied")

    async def test_stopped_meeting_exits_during_admission(self):
        await self.fixture('<p>Waiting for the host</p>')
        with self.assertRaises(MeetingJoinError) as caught:
            await _join(self.page, self.target, "Bot", should_stop=AsyncMock(return_value=True))
        self.assertEqual(caught.exception.code, "cancelled")

    async def test_expired_auth_never_fills_guest_name(self):
        await self.fixture('<p>What\u2019s your name?</p><input aria-label="Your name" type="text"><button>Ask to join</button>')
        with self.assertRaises(MeetingJoinError) as caught:
            await _join(self.page, self.target, "Bot", authenticated=True)
        self.assertEqual(caught.exception.code, "auth_session_expired")
        self.assertEqual(await self.page.locator('input').input_value(), "")

    async def test_session_only_cookies_restore_only_in_same_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "workspace-a"
            folder.mkdir()
            first = await self.browser.new_context()
            await first.add_cookies([{"name": "SID", "value": "fixture-token", "domain": ".google.com", "path": "/", "secure": True, "httpOnly": True}])
            self.assertTrue(await has_google_session(first))
            await save_auth_state(first, folder)
            await first.close()
            second = await self.browser.new_context()
            other = await self.browser.new_context()
            with patch.dict(os.environ, {"PILOT_BOT_AUTH_DIR": temp}):
                await import_auth_state(second, folder, uuid.uuid4())
                await import_auth_state(other, Path(temp) / "workspace-b", uuid.uuid4())
            self.assertTrue(await has_google_session(second))
            self.assertFalse(await has_google_session(other))
            await second.close()
            await other.close()

    async def test_profile_lock_blocks_concurrent_account_setup(self):
        with tempfile.TemporaryDirectory() as temp:
            with locked_profile(Path(temp)):
                with self.assertRaisesRegex(RuntimeError, "in use"):
                    with locked_profile(Path(temp)):
                        pass
