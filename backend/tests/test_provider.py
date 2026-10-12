import json
import unittest
from dataclasses import replace
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from app.core.app_config import APP_CONFIG
from app.services.ai_provider import AIProvider, AIProviderError, OllamaProvider, get_ai_provider
from app.services.embedding_provider import EmbeddingProviderError, OllamaEmbeddingProvider


class Example(BaseModel):
    title: str


class FakeProvider(AIProvider):
    def __init__(self, responses):
        self.responses = iter(responses)

    def chat(self, prompt, system="", schema=None):
        return next(self.responses)


class ProviderTests(unittest.TestCase):
    def test_invalid_json_is_retried_and_validated(self):
        provider = FakeProvider(["not JSON", '{"title":"Done"}'])
        self.assertEqual(provider.structured("prompt", Example).title, "Done")
        with self.assertRaises(AIProviderError):
            FakeProvider(["bad", "still bad", "wrong"]).structured("prompt", Example)

    def test_provider_and_model_switch(self):
        self.assertIsInstance(get_ai_provider(), OllamaProvider)
        changed = replace(APP_CONFIG, ai=replace(APP_CONFIG.ai, model="another-installed-model"))
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value.json.return_value = {"message": {"content": "answer"}}
        with patch("app.services.ai_provider.APP_CONFIG", changed), patch("app.services.ai_provider.httpx.Client", return_value=client):
            self.assertEqual(OllamaProvider().chat("Question"), "answer")
        self.assertEqual(client.post.call_args.kwargs["json"]["model"], "another-installed-model")

    def test_embedding_dimension_mismatch_fails(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value.json.return_value = {"embeddings": [[0.1, 0.2]]}
        with patch("app.services.embedding_provider.httpx.Client", return_value=client):
            with self.assertRaises(EmbeddingProviderError):
                OllamaEmbeddingProvider().embed(["text"])
