"""Voice output into Vexa's PulseAudio virtual microphone with process exit ACK."""
import asyncio
import json
import time
import uuid

import redis

from app.core.config import settings
from app.services.vexa_client import VexaClient, VexaError


class VexaMeetingAudioProvider:
    def __init__(self, meeting_id, workspace_id):
        self.meeting_id = meeting_id
        self.vexa = VexaClient(workspace_id)

    async def speak_text(self, text: str, voice_id: str = "lessac") -> None:
        from app.services.pilot_tts import VOICE_MODELS
        if voice_id not in VOICE_MODELS:
            raise ValueError("Unknown local voice")
        ident = f"mp/{voice_id}/{uuid.uuid4().hex}"

        def play():
            binding = self.vexa.binding(self.meeting_id)
            with redis.Redis.from_url(settings.VEXA_REDIS_URL) as bus:
                with bus.lock(f"meetpilot:voice:{binding['provider_id']}:lock", timeout=120, blocking_timeout=0):
                    with bus.pubsub(ignore_subscribe_messages=True) as sub:
                        sub.subscribe(f"meetpilot:voice:{binding['provider_id']}")
                        # Wait for subscription acknowledgement before publishing speech.
                        while not sub.subscribed:
                            sub.get_message(timeout=1)
                        self.vexa.command(self.meeting_id, {"action": "speak", "text": text, "voice": ident})
                        deadline = time.monotonic() + 110
                        while time.monotonic() < deadline:
                            message = sub.get_message(timeout=0.2)
                            if not message:
                                continue
                            event = json.loads(message["data"])
                            if event.get("interaction_id") != ident:
                                continue
                            if event.get("type") == "playback_complete":
                                return
                            if event.get("type") == "playback_interrupted":
                                raise asyncio.CancelledError()
                            if event.get("type") == "playback_failed":
                                raise VexaError("Vexa local speech synthesis or playback failed")
                        raise VexaError("Vexa did not confirm virtual microphone playback")
        try:
            await asyncio.to_thread(play)
        except asyncio.CancelledError:
            await self.interrupt()
            raise

    async def interrupt(self):
        await asyncio.to_thread(self.vexa.command, self.meeting_id, {"action": "speak_stop"})
