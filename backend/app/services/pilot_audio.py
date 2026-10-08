"""Output adapters for a local browser and the native meeting bot."""

import asyncio
import base64
import json
import time
import uuid
from abc import ABC, abstractmethod

from fastapi import WebSocket
import redis

from app.core.config import settings


class MeetingAudioProvider(ABC):
    @abstractmethod
    async def speak(self, wav: bytes, **kwargs) -> None:
        raise NotImplementedError


class WebSocketAudioProvider(MeetingAudioProvider):
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def speak(self, wav: bytes, **kwargs) -> None:
        interaction_id = kwargs.get("interaction_id")
        await self.websocket.send_json({"type": "audio_started", "format": "wav", "origin": "pilot",
                                        "bytes": len(wav), "interaction_id": interaction_id})
        await self.websocket.send_bytes(wav)
        await self.websocket.send_json({"type": "audio_ready", "origin": "pilot", "ack_required": True,
                                        "interaction_id": interaction_id})


class NativeMeetingAudioProvider(MeetingAudioProvider):
    def __init__(self, meeting_id: uuid.UUID):
        self.meeting_id = meeting_id
        self.client = redis.Redis.from_url(settings.REDIS_URL)

    async def speak(self, wav: bytes, **kwargs) -> None:
        interaction_id = uuid.uuid4().hex
        channel = f"native-meeting:{self.meeting_id}:tts"
        event_channel = f"native-meeting:{self.meeting_id}:tts-events"
        payload = json.dumps({"type": "play", "interaction_id": interaction_id, "origin": "pilot",
                              "wav_base64": base64.b64encode(wav).decode("ascii")})

        def publish_and_wait():
            if not self.client.exists(f"native-meeting:{self.meeting_id}:lock"):
                raise RuntimeError("Native meeting bot is not running")
            with self.client.pubsub(ignore_subscribe_messages=True) as sub:
                sub.subscribe(event_channel)
                if self.client.publish(channel, payload) == 0:
                    raise RuntimeError("Native meeting bot audio channel is unavailable")
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    event = sub.get_message(timeout=1)
                    if event:
                        result = json.loads(event["data"])
                        if result.get("interaction_id") == interaction_id:
                            if result.get("type") == "playback_interrupted":
                                raise asyncio.CancelledError()
                            return
                raise RuntimeError("Native meeting bot did not confirm audio playback")

        await asyncio.to_thread(publish_and_wait)

    async def interrupt(self) -> None:
        await asyncio.to_thread(
            self.client.publish, f"native-meeting:{self.meeting_id}:tts",
            json.dumps({"type": "stop"}),
        )
