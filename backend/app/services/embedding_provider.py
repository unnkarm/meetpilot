"""Embedding provider boundary with strict pgvector dimension validation."""

from abc import ABC, abstractmethod
from math import isfinite

import httpx

from app.core.app_config import APP_CONFIG
from app.services.openai_transport import OpenAIRequestError, post_openai


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        raise NotImplementedError


class OllamaEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        if not texts:
            return []
        cfg = APP_CONFIG.embeddings
        if task_type not in {"RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"}:
            raise EmbeddingProviderError(f"Unsupported embedding task type: {task_type}")
        prefix = cfg.query_prefix if task_type == "RETRIEVAL_QUERY" else cfg.document_prefix
        vectors: list[list[float]] = []
        try:
            with httpx.Client(timeout=APP_CONFIG.ai.timeout_seconds) as client:
                for offset in range(0, len(texts), cfg.batch_size):
                    batch = [prefix + value for value in texts[offset : offset + cfg.batch_size]]
                    response = client.post(
                        f"{APP_CONFIG.ollama_url.rstrip('/')}/api/embed",
                        json={"model": cfg.model, "input": batch, "truncate": True},
                    )
                    response.raise_for_status()
                    received = response.json()["embeddings"]
                    if len(received) != len(batch) or any(len(vector) != cfg.dimensions for vector in received):
                        raise EmbeddingProviderError(
                            f"Embedding model {cfg.model} must return {cfg.dimensions} dimensions for the current schema"
                        )
                    vectors.extend(received)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise EmbeddingProviderError(f"Ollama embeddings failed for model {cfg.model}: {exc}") from exc
        return vectors


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        if not texts:
            return []
        if task_type not in {"RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"}:
            raise EmbeddingProviderError(f"Unsupported embedding task type: {task_type}")
        if any(not isinstance(value, str) or not value.strip() for value in texts):
            raise EmbeddingProviderError("Embedding inputs must be nonempty text")
        cfg = APP_CONFIG.embeddings
        if cfg.model not in {"text-embedding-3-small", "text-embedding-3-large"}:
            raise EmbeddingProviderError("OpenAI embeddings require a text-embedding-3 model for vector(768)")
        vectors = []
        for offset in range(0, len(texts), cfg.batch_size):
            batch = texts[offset:offset + cfg.batch_size]
            try:
                result = post_openai("embeddings", {
                    "model": cfg.model, "input": batch, "dimensions": cfg.dimensions, "encoding_format": "float",
                }, timeout=APP_CONFIG.ai.timeout_seconds)
            except OpenAIRequestError as exc:
                raise EmbeddingProviderError(str(exc)) from None
            rows = result.get("data")
            if not isinstance(rows, list) or len(rows) != len(batch):
                raise EmbeddingProviderError("OpenAI returned the wrong number of embeddings")
            ordered = {}
            for row in rows:
                if not isinstance(row, dict):
                    raise EmbeddingProviderError("OpenAI returned invalid embedding data")
                index, vector = row.get("index"), row.get("embedding")
                if (type(index) is not int or not 0 <= index < len(batch) or index in ordered
                        or not isinstance(vector, list) or len(vector) != cfg.dimensions
                        or any(type(value) not in (int, float) or not isfinite(value) for value in vector)):
                    raise EmbeddingProviderError(f"OpenAI must return indexed finite {cfg.dimensions}-dimension vectors")
                ordered[index] = [float(value) for value in vector]
            vectors.extend(ordered[index] for index in range(len(batch)))
        return vectors


def get_embedding_provider() -> EmbeddingProvider:
    if not APP_CONFIG.embeddings.enabled:
        raise EmbeddingProviderError("Embeddings are disabled")
    if APP_CONFIG.embeddings.provider == "ollama":
        return OllamaEmbeddingProvider()
    if APP_CONFIG.embeddings.provider == "openai":
        return OpenAIEmbeddingProvider()
    raise EmbeddingProviderError(f"Unsupported embedding provider: {APP_CONFIG.embeddings.provider}")


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    return get_embedding_provider().embed([text], task_type)[0]


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    return get_embedding_provider().embed(texts, task_type)
