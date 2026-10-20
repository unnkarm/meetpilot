"""Cloud provider contracts without network calls, model downloads or charges."""

import json
import os
import unittest
from copy import deepcopy
from dataclasses import replace
from unittest.mock import MagicMock, patch

import httpx
from pydantic import BaseModel, Field, SecretStr

from app.core.app_config import APP_CONFIG, AIConfig, EmbeddingConfig
from app.core.config import Settings
from app.services.ai_provider import (
    AIProviderError, OpenAIResponsesProvider, get_ai_provider, openai_strict_schema,
)
from app.services.embedding_provider import (
    EmbeddingProviderError, OpenAIEmbeddingProvider, get_embedding_provider,
)
from app.services.openai_transport import OpenAIRequestError, post_openai


class Point(BaseModel):
    text: str = Field(min_length=1)
    quote: str | None = None


class Answer(BaseModel):
    title: str
    points: list[Point] = Field(default_factory=list)


def completed(value):
    return {"status": "completed", "output": [
        {"type": "reasoning", "summary": []},
        {"type": "message", "content": [{"type": "output_text", "text": value}]},
    ]}


class SaaSProviderTests(unittest.TestCase):
    def setUp(self):
        self.config = replace(APP_CONFIG, ai=replace(APP_CONFIG.ai, provider="openai", model="configured-model"),
                              embeddings=replace(APP_CONFIG.embeddings, provider="openai", model="text-embedding-3-small"))

    def test_explicit_environment_selects_independent_models(self):
        with patch.dict(os.environ, {"AI_PROVIDER": " OpenAI ", "OPENAI_CHAT_MODEL": "chosen-model",
                                     "EMBEDDING_PROVIDER": "openai", "OPENAI_EMBEDDING_MODEL": "text-embedding-3-large"}):
            self.assertEqual(AIConfig().provider, "openai")
            self.assertEqual(AIConfig().model, "chosen-model")
            self.assertEqual(EmbeddingConfig().model, "text-embedding-3-large")
        with patch.dict(os.environ, {"AI_PROVIDER": "ollama", "EMBEDDING_PROVIDER": "ollama"}):
            self.assertNotEqual(AIConfig().model, "chosen-model")
            self.assertEqual(EmbeddingConfig().provider, "ollama")

    def test_cloud_vectors_have_a_distinct_index_namespace(self):
        model = self.config.embeddings.model
        local = replace(self.config.embeddings, provider="ollama")
        self.assertEqual(local.index_key, model)
        self.assertEqual(self.config.embeddings.index_key, "openai:text-embedding-3-small:768")
        self.assertNotEqual(local.index_key, self.config.embeddings.index_key)

    def test_secret_is_masked_in_settings(self):
        settings = Settings(OPENAI_API_KEY="test-secret")
        self.assertIsInstance(settings.OPENAI_API_KEY, SecretStr)
        self.assertNotIn("test-secret", repr(settings))

    def test_factories_do_not_make_requests(self):
        with patch("app.services.ai_provider.APP_CONFIG", self.config), \
                patch("app.services.embedding_provider.APP_CONFIG", self.config), \
                patch("app.services.openai_transport.httpx.Client") as client:
            self.assertIsInstance(get_ai_provider(), OpenAIResponsesProvider)
            self.assertIsInstance(get_embedding_provider(), OpenAIEmbeddingProvider)
            client.assert_not_called()

    def test_strict_schema_preserves_nullable_nested_fields_and_original(self):
        original = Answer.model_json_schema()
        copied = deepcopy(original)
        converted = openai_strict_schema(original)
        self.assertEqual(original, copied)
        self.assertEqual(converted["required"], ["title", "points"])
        self.assertFalse(converted["additionalProperties"])
        point = converted["$defs"]["Point"]
        self.assertEqual(point["required"], ["text", "quote"])
        self.assertFalse(point["additionalProperties"])
        self.assertNotIn("default", point["properties"]["quote"])
        self.assertIn({"type": "null"}, point["properties"]["quote"]["anyOf"])

    def test_strict_schema_does_not_drop_a_property_named_default(self):
        result = openai_strict_schema({"type": "object", "properties": {"default": {"type": "string"}}})
        self.assertIn("default", result["properties"])
        with self.assertRaises(AIProviderError):
            openai_strict_schema({"type": "object", "additionalProperties": {"type": "string"}})

    def test_responses_contract_keeps_validation_and_skips_reasoning(self):
        response = completed('{"title":"Review","points":[{"text":"Database","quote":null}]}')
        with patch("app.services.ai_provider.APP_CONFIG", self.config), \
                patch("app.services.ai_provider.post_openai", return_value=response) as request:
            answer = get_ai_provider().structured("private source", Answer, system="Use evidence only")
        self.assertEqual(answer.points[0].text, "Database")
        path, payload = request.call_args.args
        self.assertEqual(path, "responses")
        self.assertEqual(payload["model"], "configured-model")
        self.assertFalse(payload["store"])
        self.assertEqual(payload["instructions"], "Use evidence only")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertNotIn("temperature", payload)
        self.assertNotIn("options", payload)

    def test_partial_refused_empty_and_malformed_outputs_fail(self):
        cases = [
            {"status": "incomplete", "output": completed("partial")["output"]},
            {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]},
            completed(" "), {"status": "completed", "output": {}},
            {"status": "completed", "output": [{"type": "message", "content": None}]},
            {"status": "completed", "output": [{"type": "message", "content": [None]}]},
        ]
        for value in cases:
            with self.subTest(value=value), patch("app.services.ai_provider.APP_CONFIG", self.config), \
                    patch("app.services.ai_provider.post_openai", return_value=value):
                with self.assertRaises(AIProviderError):
                    OpenAIResponsesProvider().chat("Question")

    def test_no_model_or_key_rejected_before_network(self):
        with patch("app.services.ai_provider.APP_CONFIG", replace(self.config, ai=replace(self.config.ai, model=""))), \
                patch("app.services.ai_provider.post_openai") as request:
            with self.assertRaises(AIProviderError):
                OpenAIResponsesProvider().chat("Question")
            request.assert_not_called()
        with patch("app.services.openai_transport.settings") as settings, \
                patch("app.services.openai_transport.httpx.Client") as client:
            settings.OPENAI_API_KEY = SecretStr("")
            with self.assertRaises(OpenAIRequestError):
                post_openai("responses", {}, timeout=1)
            client.assert_not_called()

    def test_transport_uses_fixed_origin_and_redacts_errors(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value.status_code = 429
        client.post.return_value.text = "test-secret private prompt"
        with patch("app.services.openai_transport.settings") as settings, \
                patch("app.services.openai_transport.httpx.Client", return_value=client) as factory:
            settings.OPENAI_API_KEY = SecretStr("test-secret")
            with self.assertRaisesRegex(OpenAIRequestError, r"HTTP 429") as failure:
                post_openai("responses", {"input": "private prompt"}, timeout=3)
            self.assertNotIn("test-secret", str(failure.exception))
            self.assertNotIn("private prompt", str(failure.exception))
            self.assertEqual(client.post.call_args.args[0], "https://api.openai.com/v1/responses")
            self.assertFalse(factory.call_args.kwargs["follow_redirects"])
            client.post.side_effect = httpx.ConnectError("test-secret private prompt")
            with self.assertRaisesRegex(OpenAIRequestError, "connection failed") as failure:
                post_openai("responses", {}, timeout=3)
            self.assertNotIn("test-secret", str(failure.exception))

    def test_embeddings_are_ordered_and_do_not_use_nomic_prefixes(self):
        rows = [{"index": 1, "embedding": [0.2] * 768}, {"index": 0, "embedding": [0.1] * 768}]
        with patch("app.services.embedding_provider.APP_CONFIG", self.config), \
                patch("app.services.embedding_provider.post_openai", return_value={"data": rows}) as request:
            vectors = get_embedding_provider().embed(["first", "second"], "RETRIEVAL_QUERY")
        self.assertEqual(vectors[0], [0.1] * 768)
        self.assertEqual(vectors[1], [0.2] * 768)
        self.assertEqual(request.call_args.args[1]["input"], ["first", "second"])
        self.assertEqual(request.call_args.args[1]["dimensions"], 768)

    def test_embedding_bad_count_index_dimensions_or_values_fail(self):
        vector = [0.1] * 768
        cases = [[], [{"index": 0, "embedding": [0.1]}], [{"index": 1, "embedding": vector}],
                 [{"index": True, "embedding": vector}], [{"index": 0, "embedding": [float("nan")] * 768}],
                 [{"index": 0, "embedding": [True] * 768}]]
        for rows in cases:
            with self.subTest(rows=str(rows)[:50]), patch("app.services.embedding_provider.APP_CONFIG", self.config), \
                    patch("app.services.embedding_provider.post_openai", return_value={"data": rows}):
                with self.assertRaises(EmbeddingProviderError):
                    OpenAIEmbeddingProvider().embed(["first"])
        with patch("app.services.embedding_provider.APP_CONFIG", self.config), \
                patch("app.services.embedding_provider.post_openai", return_value={"data": [{"index": 0, "embedding": vector}] * 2}):
            with self.assertRaises(EmbeddingProviderError):
                OpenAIEmbeddingProvider().embed(["first", "second"])

    def test_embedding_empty_input_and_unknown_model_do_not_charge(self):
        with patch("app.services.embedding_provider.APP_CONFIG", self.config), \
                patch("app.services.embedding_provider.post_openai") as request:
            self.assertEqual(OpenAIEmbeddingProvider().embed([]), [])
            with self.assertRaises(EmbeddingProviderError):
                OpenAIEmbeddingProvider().embed([" "])
            request.assert_not_called()
        config = replace(self.config, embeddings=replace(self.config.embeddings, model="unknown-model"))
        with patch("app.services.embedding_provider.APP_CONFIG", config), \
                patch("app.services.embedding_provider.post_openai") as request:
            with self.assertRaises(EmbeddingProviderError):
                OpenAIEmbeddingProvider().embed(["test"])
            request.assert_not_called()

    def test_cloud_structured_output_still_retries_invalid_json(self):
        with patch("app.services.ai_provider.APP_CONFIG", self.config), \
                patch("app.services.ai_provider.post_openai", side_effect=[completed("bad"), completed(json.dumps({"title": "OK", "points": []}))]) as request:
            self.assertEqual(OpenAIResponsesProvider().structured("test", Answer).title, "OK")
            self.assertEqual(request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
