"""Provider boundary for text generation. Business services never call vendor SDKs."""

import json
import logging
from abc import ABC, abstractmethod
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.app_config import APP_CONFIG

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class AIProviderError(RuntimeError):
    pass


class AIProvider(ABC):
    @abstractmethod
    def chat(self, prompt: str, system: str = "", schema: dict | None = None) -> str:
        raise NotImplementedError

    def structured(self, prompt: str, schema: type[T], system: str = "") -> T:
        last_error: Exception | None = None
        repair = ""
        for attempt in range(APP_CONFIG.ai.retries + 1):
            raw = self.chat(prompt + repair, system, schema.model_json_schema())
            try:
                return schema.model_validate(json.loads(raw))
            except (ValueError, ValidationError) as exc:
                last_error = exc
                logger.warning("Invalid structured AI output, attempt %s: %s", attempt + 1, exc)
                repair = "\nYour previous answer failed schema validation. Return ONLY valid JSON matching the schema."
        raise AIProviderError("AI returned invalid structured output") from last_error


class OllamaProvider(AIProvider):
    def chat(self, prompt: str, system: str = "", schema: dict | None = None) -> str:
        cfg = APP_CONFIG.ai
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": cfg.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": cfg.temperature, "num_predict": cfg.max_tokens, "num_ctx": cfg.context_tokens},
        }
        if schema is not None:
            payload["format"] = schema
        try:
            with httpx.Client(timeout=cfg.timeout_seconds) as client:
                response = client.post(f"{APP_CONFIG.ollama_url.rstrip('/')}/api/chat", json=payload)
                response.raise_for_status()
                content = response.json()["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise AIProviderError("Ollama returned an empty response")
            return content
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise AIProviderError(f"Ollama chat failed for model {cfg.model}: {exc}") from exc


def get_ai_provider() -> AIProvider:
    if not APP_CONFIG.ai.enabled:
        raise AIProviderError("AI generation is disabled")
    if APP_CONFIG.ai.provider == "ollama":
        return OllamaProvider()
    raise AIProviderError(f"Unsupported AI provider: {APP_CONFIG.ai.provider}")
