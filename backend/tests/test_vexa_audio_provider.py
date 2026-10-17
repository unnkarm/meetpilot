"""Voice ACK and cancellation regressions; no Redis, bot, or AI model required."""

import asyncio
import json
import queue
import threading
import time
import unittest
import uuid
from unittest.mock import Mock, patch

from app.core.config import settings
from app.services.vexa_audio_provider import VexaMeetingAudioProvider
from app.services.vexa_client import VexaError


class FakePubSub:
    def __init__(self, bus):
        self.bus = bus
        self.events = queue.Queue()
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True
        self.bus.subscribers.remove(self)

    def subscribe(self, channel):
        if self.bus.subscription_ack:
            self.events.put({"type": "subscribe", "channel": channel, "data": 1})

    def get_message(self, timeout):
        try:
            return self.events.get(timeout=timeout)
        except queue.Empty:
            return None


class FakeLock:
    def __init__(self, bus):
        self.bus = bus

    def __enter__(self):
        if not self.bus.voice_lock.acquire(blocking=False):
            raise RuntimeError("Old playback still holds the voice lock")
        return self

    def __exit__(self, *args):
        self.bus.voice_lock.release()


class FakeBus:
    def __init__(self):
        self.voice_lock = threading.Lock()
        self.subscribers = []
        self.commands = []
        self.subscription_ack = True
        self.command_subscribers = 1
        self.stop_ack = True
        self.on_speak = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def lock(self, *args, **kwargs):
        return FakeLock(self)

    def pubsub(self, **kwargs):
        subscriber = FakePubSub(self)
        self.subscribers.append(subscriber)
        return subscriber

    def emit(self, kind, ident):
        for subscriber in self.subscribers[:]:
            subscriber.events.put({"type": "message", "data": json.dumps({
                "type": kind, "interaction_id": ident,
            })})

    def publish(self, channel, raw):
        command = json.loads(raw)
        self.commands.append(command)
        if self.command_subscribers and command["action"] == "speak" and self.on_speak:
            self.on_speak(command)
        if command["action"] == "speak_stop" and self.stop_ack:
            self.emit("playback_interrupted", command.get("interaction_id"))
        return self.command_subscribers


class VexaAudioProviderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.client = Mock()
        self.client.binding.return_value = {"provider_id": 71}
        self.client.cache.get.return_value = json.dumps({"state": "active"})
        factory = patch("app.services.vexa_audio_provider.VexaClient", return_value=self.client)
        factory.start()
        self.addCleanup(factory.stop)
        redis = patch("app.services.vexa_audio_provider.redis.Redis.from_url", return_value=self.bus)
        redis.start()
        self.addCleanup(redis.stop)
        config = patch.object(settings, "VEXA_REDIS_URL", "redis://private-test-bus")
        config.start()
        self.addCleanup(config.stop)
        self.provider = VexaMeetingAudioProvider(uuid.uuid4(), uuid.uuid4())
        self.provider.STOP_TIMEOUT = 0.03
        self.provider.POLL_INTERVAL = 0.005

    async def test_completion_is_correlated_and_ignores_old_playback_ack(self):
        def reply(command):
            self.bus.emit("playback_complete", "old-interaction")
            self.bus.emit("playback_started", command["voice"])
            self.bus.emit("playback_complete", command["voice"])
        self.bus.on_speak = reply
        await self.provider.speak_text("We agreed to review the migration on Friday.")
        self.assertEqual([row["action"] for row in self.bus.commands], ["speak"])
        self.assertFalse(self.bus.voice_lock.locked())
        self.assertFalse(self.bus.subscribers)
        self.client.command.assert_not_called()

    async def test_native_reply_language_travels_on_the_same_correlated_command(self):
        from app.services.pilot_tts import parse_voice_language, parse_voice_token
        self.bus.on_speak = lambda command: self.bus.emit("playback_complete", command["voice"])
        await self.provider.speak_text("আমরা PostgreSQL ঠিক করেছি।", "ryan", language="bn")
        command = self.bus.commands[0]
        self.assertEqual(parse_voice_language(command["voice"]), "bn")
        self.assertEqual(parse_voice_token(command["voice"]), "ryan")
        self.assertFalse(self.bus.voice_lock.locked())

    async def test_cancellation_stops_thread_releases_lock_and_next_reply_plays(self):
        started = threading.Event()
        self.bus.on_speak = lambda command: started.set()
        playback = asyncio.create_task(self.provider.speak_text("First answer."))
        deadline = time.monotonic() + 1
        while not started.is_set():
            self.assertLess(time.monotonic(), deadline)
            await asyncio.sleep(0.005)
        cancelled_at = time.monotonic()
        playback.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(playback, timeout=0.5)
        self.assertLess(time.monotonic() - cancelled_at, 0.5)
        self.assertFalse(self.bus.voice_lock.locked())
        self.assertFalse(self.bus.subscribers)
        self.assertEqual(self.bus.commands[1], {"action": "speak_stop",
                                               "interaction_id": self.bus.commands[0]["voice"]})
        self.bus.on_speak = lambda command: self.bus.emit("playback_complete", command["voice"])
        await self.provider.speak_text("The follow-up answer.")
        self.assertEqual([row["action"] for row in self.bus.commands], ["speak", "speak_stop", "speak"])

    async def test_failed_playback_stops_pending_output_and_releases_lock(self):
        self.bus.on_speak = lambda command: self.bus.emit("playback_failed", command["voice"])
        with self.assertRaisesRegex(VexaError, "synthesis or playback failed"):
            await self.provider.speak_text("Answer.")
        self.assertEqual(self.bus.commands[-1]["action"], "speak_stop")
        self.assertFalse(self.bus.voice_lock.locked())
        self.bus.on_speak = lambda command: self.bus.emit("playback_complete", command["voice"])
        await self.provider.speak_text("Try the following turn.")

    async def test_repeated_cancellation_still_joins_the_lock_owner(self):
        self.bus.stop_ack = False
        self.provider.STOP_TIMEOUT = 0.06
        started = threading.Event()
        self.bus.on_speak = lambda command: started.set()
        playback = asyncio.create_task(self.provider.speak_text("First answer."))
        deadline = time.monotonic() + 1
        while not started.is_set():
            self.assertLess(time.monotonic(), deadline)
            await asyncio.sleep(0.005)
        playback.cancel()
        while len(self.bus.commands) < 2:
            self.assertLess(time.monotonic(), deadline)
            await asyncio.sleep(0.005)
        self.assertTrue(self.bus.voice_lock.locked())
        playback.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await playback
        self.assertFalse(self.bus.voice_lock.locked())
        self.assertFalse(self.bus.subscribers)

    async def test_interrupted_ack_propagates_cancellation_without_stopping_new_turn(self):
        self.bus.on_speak = lambda command: self.bus.emit("playback_interrupted", command["voice"])
        with self.assertRaises(asyncio.CancelledError):
            await self.provider.speak_text("Interrupted answer.")
        self.assertEqual([row["action"] for row in self.bus.commands], ["speak"])
        self.assertFalse(self.bus.voice_lock.locked())

    async def test_ack_timeout_cancels_orphan_output(self):
        self.provider.PLAYBACK_TIMEOUT = 0.02
        with self.assertRaisesRegex(VexaError, "did not confirm"):
            await self.provider.speak_text("Unacknowledged answer.")
        self.assertEqual(self.bus.commands[-1]["action"], "speak_stop")
        self.assertFalse(self.bus.voice_lock.locked())

    async def test_missing_subscription_ack_does_not_dispatch_speech(self):
        self.bus.subscription_ack = False
        self.provider.SUBSCRIPTION_TIMEOUT = 0.02
        with self.assertRaisesRegex(VexaError, "acknowledgement channel"):
            await self.provider.speak_text("No acknowledgement channel.")
        self.assertEqual(self.bus.commands, [])
        self.assertFalse(self.bus.voice_lock.locked())

    async def test_no_bot_subscriber_is_reported_instead_of_waiting_for_ack(self):
        self.bus.command_subscribers = 0
        with self.assertRaisesRegex(VexaError, "command channel"):
            await self.provider.speak_text("Nobody is listening.")
        self.assertFalse(self.bus.voice_lock.locked())

    async def test_workspace_binding_is_required_before_any_command(self):
        self.client.binding.side_effect = VexaError("Vexa meeting does not belong to this workspace")
        with self.assertRaisesRegex(VexaError, "workspace"):
            await self.provider.speak_text("Forbidden.")
        with self.assertRaisesRegex(VexaError, "workspace"):
            await self.provider.interrupt()
        self.assertEqual(self.bus.commands, [])

    async def test_interrupt_uses_private_bus_without_slow_gateway_query(self):
        await self.provider.interrupt()
        self.client.binding.assert_called_once_with(self.provider.meeting_id)
        self.client.command.assert_not_called()
        self.assertEqual(self.bus.commands, [{"action": "speak_stop"}])

    async def test_speech_requires_joined_bot_but_stop_can_cancel_a_pending_join(self):
        self.client.cache.get.return_value = json.dumps({"state": "awaiting_admission"})
        with self.assertRaisesRegex(VexaError, "not active"):
            await self.provider.speak_text("Do not speak in the waiting room.")
        self.assertEqual(self.bus.commands, [])
        await self.provider.interrupt()
        self.assertEqual(self.bus.commands, [{"action": "speak_stop"}])


if __name__ == "__main__":
    unittest.main()
