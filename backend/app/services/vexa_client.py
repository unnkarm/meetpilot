"""Workspace-scoped bridge to the unmodified, self-hosted Vexa bot engine."""
import json
import uuid
import time
from urllib.parse import quote

import httpx
import redis

from app.core.config import settings


class VexaError(RuntimeError):
    pass


class VexaUnavailable(VexaError):
    """A temporary engine/network failure; retain the live bridge and retry."""


class VexaClient:
    def __init__(self, workspace_id: uuid.UUID):
        self.workspace_id = uuid.UUID(str(workspace_id))
        self.cache = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    def _admin(self, method: str, path: str, **kwargs):
        if not settings.VEXA_ADMIN_TOKEN:
            raise VexaError("Vexa credentials are missing. Run python backend/scripts/setup_vexa.py and restart Docker Compose.")
        return httpx.request(method, settings.VEXA_ADMIN_URL.rstrip("/") + path,
                             headers={"X-Admin-API-Key": settings.VEXA_ADMIN_TOKEN}, timeout=30, **kwargs)

    def api_key(self) -> str:
        key = f"vexa:workspace:{self.workspace_id}:key"
        token = self.cache.get(key)
        if token:
            return token
        with self.cache.lock(key + ":provision", timeout=90, blocking_timeout=35):
            token = self.cache.get(key)
            if token:
                return token
            email = f"workspace-{self.workspace_id}@meetpilot.local"
            response = self._admin("GET", "/admin/users/email/" + quote(email, safe=""))
            if response.status_code == 404:
                response = self._admin("POST", "/admin/users", json={"email": email, "name": "MeetPilot workspace"})
            response.raise_for_status()
            user_id = response.json()["id"]
            response = self._admin("POST", f"/admin/users/{user_id}/tokens", json={"scopes": ["bot", "tx"], "name": "MeetPilot bridge"})
            response.raise_for_status()
            token = response.json().get("token") or response.json().get("api_token")
            if not token:
                raise VexaError("Vexa did not return a workspace API key")
            self.cache.set(key, token)
            self.cache.set(f"vexa:workspace:{self.workspace_id}:user", user_id)
            return token

    def request(self, method: str, path: str, **kwargs) -> dict:
        try:
            attempts = 4 if method == "GET" else 2
            for attempt in range(attempts):
                response = httpx.request(method, settings.VEXA_API_URL.rstrip("/") + path,
                                         headers={"X-API-Key": self.api_key()}, timeout=45, **kwargs)
                if response.status_code == 401 and attempt == 0:
                    self.cache.delete(f"vexa:workspace:{self.workspace_id}:key")
                    continue
                if response.status_code in {429, 502, 503, 504}:
                    if method == "GET" and attempt < attempts - 1:
                        time.sleep(min(2 ** attempt, 4))
                        continue
                    raise VexaUnavailable("Vexa is temporarily unavailable; the bridge will reconnect")
                if response.status_code >= 400:
                    # Do not leak upstream URLs, cookies or credential-bearing diagnostics.
                    raise VexaError(f"Vexa rejected {method} {path.split('?')[0]} (HTTP {response.status_code})")
                return response.json() if response.content else {}
        except httpx.RequestError as exc:
            raise VexaUnavailable("The local Vexa engine is unreachable. Check docker compose logs vexa and its health status.") from exc
        raise VexaError("Vexa authentication failed")

    def preflight(self) -> None:
        self.request("GET", "/bots/status")

    def start(self, meeting_url: str, bot_name: str, language: str | None = None) -> dict:
        # Let upstream's own parser preserve Teams IDs, Zoom passcodes and host variants.
        from app.services.meeting_language import recognition_hint
        return self.request("POST", "/bots", json={"meeting_url": meeting_url, "bot_name": bot_name,
                                                   "language": recognition_hint(language),
                                                   "transcribe_enabled": True, "recording_enabled": True,
                                                   "automatic_leave": {"max_wait_for_admission": 300000}})

    def meeting(self, provider_id: int) -> dict:
        return self.request("GET", f"/meetings/{int(provider_id)}")

    def transcript(self, provider_id: int) -> dict:
        return self.request("GET", f"/transcripts/by-id/{int(provider_id)}")

    def stop(self, platform: str, native_id: str) -> dict:
        return self.request("DELETE", f"/bots/{quote(platform, safe='')}/{quote(native_id, safe='')}")

    def binding(self, meeting_id: uuid.UUID) -> dict:
        raw = self.cache.get(f"vexa:meeting:{meeting_id}:binding")
        if not raw:
            raise VexaError("The Vexa bot has not started for this meeting")
        binding = json.loads(raw)
        if binding.get("workspace_id") != str(self.workspace_id):
            raise VexaError("Vexa meeting does not belong to this workspace")
        return binding

    def command(self, meeting_id: uuid.UUID, payload: dict) -> None:
        binding = self.binding(meeting_id)
        # Resolve through the workspace key before using the private acts.v1 bus.
        provider_meeting = self.meeting(binding["provider_id"])
        if provider_meeting.get("status") != "active":
            raise VexaError("The Vexa bot is not active in the meeting")
        if not settings.VEXA_REDIS_URL:
            raise VexaError("Vexa command bus is not configured")
        with redis.Redis.from_url(settings.VEXA_REDIS_URL) as bus:
            if not bus.publish(f"bot_commands:meeting:{binding['provider_id']}", json.dumps(payload)):
                raise VexaError("Vexa bot command channel is unavailable")
