"""Voice output into Vexa's PulseAudio virtual microphone with process exit ACK."""
import asyncio
import json
import threading
import time
import uuid

import redis

from app.core.config import settings
from app.services.vexa_client import VexaClient, VexaError


class _PlaybackInterrupted(Exception):
    pass


class VexaMeetingAudioProvider:
    PLAYBACK_TIMEOUT = 110.0
    SUBSCRIPTION_TIMEOUT = 3.0
    STOP_TIMEOUT = 1.0
    POLL_INTERVAL = 0.05

    def __init__(self, meeting_id, workspace_id):
        self.meeting_id = meeting_id
        self.vexa = VexaClient(workspace_id)

    async def speak_text(self, text: str, voice_id: str = "lessac", language: str | None = None) -> None:
        from app.services.pilot_tts import VOICE_MODELS
        if voice_id not in VOICE_MODELS:
            raise ValueError("Unknown local voice")
        ident = f"mp/{voice_id}/{uuid.uuid4().hex}"
        if language in {"bn", "hi"}:
            ident += "/" + language
        cancelled = threading.Event()

        def play():
            # This binding is checked against the authenticated workspace by
            # VexaClient. The private command bus also confirms a bot subscriber.
            # A gateway HTTP lookup here used to delay barge-in for tens of seconds.
            binding = self.vexa.binding(self.meeting_id)
            try:
                status = json.loads(self.vexa.cache.get(f"native-meeting:{self.meeting_id}:status") or "{}")
            except (ValueError, TypeError):
                status = {}
            if not isinstance(status, dict) or status.get("state") not in {"active", "reconnecting"}:
                raise VexaError("The Vexa bot is not active in the meeting")
            if not settings.VEXA_REDIS_URL:
                raise VexaError("Vexa command bus is not configured")
            with redis.Redis.from_url(settings.VEXA_REDIS_URL,
                                      socket_connect_timeout=2, socket_timeout=2) as bus:
                with bus.lock(f"meetpilot:voice:{binding['provider_id']}:lock", timeout=120,
                              blocking_timeout=0):
                    with bus.pubsub(ignore_subscribe_messages=False) as sub:
                        sub.subscribe(f"meetpilot:voice:{binding['provider_id']}")
                        # Wait for subscription acknowledgement before publishing speech.
                        deadline = time.monotonic() + self.SUBSCRIPTION_TIMEOUT
                        while True:
                            if cancelled.is_set():
                                return
                            message = sub.get_message(timeout=self.POLL_INTERVAL)
                            if message and message.get("type") == "subscribe":
                                break
                            if time.monotonic() >= deadline:
                                raise VexaError("Vexa voice acknowledgement channel is unavailable")
                        channel = f"bot_commands:meeting:{binding['provider_id']}"
                        if cancelled.is_set():
                            return
                        dispatched = False
                        complete = False
                        try:
                            if not bus.publish(channel, json.dumps({"action": "speak", "text": text,
                                                                    "voice": ident})):
                                raise VexaError("Vexa bot command channel is unavailable")
                            dispatched = True
                            deadline = time.monotonic() + self.PLAYBACK_TIMEOUT
                            while time.monotonic() < deadline:
                                if cancelled.is_set():
                                    return
                                event = self._voice_event(sub.get_message(timeout=self.POLL_INTERVAL), ident)
                                if not event:
                                    continue
                                if event == "playback_complete":
                                    complete = True
                                    return
                                if event == "playback_interrupted":
                                    complete = True
                                    raise _PlaybackInterrupted()
                                if event == "playback_failed":
                                    raise VexaError("Vexa local speech synthesis or playback failed")
                            raise VexaError("Vexa did not confirm virtual microphone playback")
                        finally:
                            if dispatched and not complete:
                                # Stop before releasing the shared lock. Cancellation of
                                # asyncio.to_thread alone never stops its worker thread.
                                bus.publish(channel, json.dumps({"action": "speak_stop",
                                                                 "interaction_id": ident}))
                                deadline = time.monotonic() + self.STOP_TIMEOUT
                                while time.monotonic() < deadline:
                                    event = self._voice_event(sub.get_message(timeout=self.POLL_INTERVAL), ident)
                                    if event in {"playback_complete", "playback_interrupted", "playback_failed"}:
                                        break
        worker = asyncio.create_task(asyncio.to_thread(play))
        try:
            # Shield only the worker future, so cancellation can signal and join
            # its actual thread before a following response acquires the lock.
            await asyncio.shield(worker)
        except _PlaybackInterrupted:
            raise asyncio.CancelledError() from None
        except asyncio.CancelledError:
            cancelled.set()
            while True:
                try:
                    await asyncio.shield(worker)
                    break
                except asyncio.CancelledError:
                    if worker.done():
                        break
                    # A second barge-in/disconnect cancellation must not abandon
                    # the first worker while it still owns the shared voice lock.
                except Exception:
                    break
            raise

    @staticmethod
    def _voice_event(message, ident):
        if not message or message.get("type") != "message":
            return None
        try:
            event = json.loads(message["data"])
        except (ValueError, TypeError, KeyError):
            return None
        if not isinstance(event, dict) or event.get("interaction_id") != ident:
            return None
        return event.get("type")

    async def interrupt(self):
        def stop():
            binding = self.vexa.binding(self.meeting_id)
            if not settings.VEXA_REDIS_URL:
                raise VexaError("Vexa command bus is not configured")
            with redis.Redis.from_url(settings.VEXA_REDIS_URL,
                                      socket_connect_timeout=2, socket_timeout=2) as bus:
                if not bus.publish(f"bot_commands:meeting:{binding['provider_id']}",
                                   json.dumps({"action": "speak_stop"})):
                    raise VexaError("Vexa bot command channel is unavailable")
        await asyncio.to_thread(stop)
