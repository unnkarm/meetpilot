"""Provider boundary for text generation. Business services never call vendor SDKs."""

import json
import logging
import re
from copy import deepcopy
from abc import ABC, abstractmethod
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.app_config import APP_CONFIG
from app.services.openai_transport import OpenAIRequestError, post_openai

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
                # Validation errors may contain private transcript/model values.
                logger.warning("Invalid structured AI output, attempt %s", attempt + 1)
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


def openai_strict_schema(schema: dict) -> dict:
    """Adapt Pydantic object schemas to Structured Outputs without mutating them."""
    result = deepcopy(schema)

    def visit(node):
        if not isinstance(node, dict):
            return
        node.pop("default", None)
        if node.get("type") == "object" or "properties" in node:
            properties = node.get("properties", {})
            # Free-form maps cannot be faithfully represented in strict mode.
            if node.get("additionalProperties") not in (None, False):
                raise AIProviderError("OpenAI structured output requires named object fields")
            node["required"] = list(properties)
            node["additionalProperties"] = False
        # Traverse schema nodes only: a property named 'default' is valid data.
        for key in ("properties", "$defs", "definitions"):
            for child in node.get(key, {}).values():
                visit(child)
        for key in ("items", "not", "if", "then", "else"):
            visit(node.get(key))
        for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
            for child in node.get(key, []):
                visit(child)

    visit(result)
    if result.get("type") != "object":
        raise AIProviderError("OpenAI structured output requires an object schema")
    return result


class OpenAIResponsesProvider(AIProvider):
    def chat(self, prompt: str, system: str = "", schema: dict | None = None) -> str:
        cfg = APP_CONFIG.ai
        if not cfg.model:
            raise AIProviderError("OPENAI_CHAT_MODEL must name an available Responses API model")
        payload = {"model": cfg.model, "input": prompt, "store": False,
                   "max_output_tokens": cfg.max_tokens}
        if system:
            payload["instructions"] = system
        if schema is not None:
            name = re.sub(r"[^a-zA-Z0-9_-]", "_", str(schema.get("title", "MeetPilotOutput")))[:64]
            payload["text"] = {"format": {"type": "json_schema", "name": name or "MeetPilotOutput",
                                          "strict": True, "schema": openai_strict_schema(schema)}}
        # Do not send Ollama-only options or temperature to models that may reject
        # it. Existing Pydantic validation and evidence checks still apply.
        try:
            result = post_openai("responses", payload, timeout=cfg.timeout_seconds)
        except OpenAIRequestError as exc:
            raise AIProviderError(str(exc)) from None
        if result.get("status") != "completed":
            raise AIProviderError("OpenAI did not complete the response; no partial answer was accepted")
        output = result.get("output")
        if not isinstance(output, list):
            raise AIProviderError("OpenAI returned invalid output")
        parts = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue  # Reasoning items are not spoken or stored as answers.
            content = item.get("content")
            if not isinstance(content, list):
                raise AIProviderError("OpenAI returned invalid message content")
            for block in content:
                if not isinstance(block, dict):
                    raise AIProviderError("OpenAI returned invalid message content")
                if block.get("type") == "refusal":
                    raise AIProviderError("OpenAI declined the request")
                if block.get("type") == "output_text":
                    value = block.get("text")
                    if not isinstance(value, str):
                        raise AIProviderError("OpenAI returned invalid answer text")
                    parts.append(value)
        answer = "".join(parts)
        if not answer.strip():
            raise AIProviderError("OpenAI returned an empty answer")
        return answer


def get_ai_provider() -> AIProvider:
    if not APP_CONFIG.ai.enabled:
        raise AIProviderError("AI generation is disabled")
    if APP_CONFIG.ai.provider == "ollama":
        return OllamaProvider()
    if APP_CONFIG.ai.provider == "openai":
        return OpenAIResponsesProvider()
    raise AIProviderError(f"Unsupported AI provider: {APP_CONFIG.ai.provider}")
