import json
import logging
import mimetypes
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import ClientError
except (ImportError, AttributeError):
    from unittest.mock import MagicMock
    genai = MagicMock()
    types = MagicMock()
    ClientError = Exception

from app.core.config import settings
from app.core.rate_limiter import RateLimitError, gemini_rate_limiter

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _extract_retry_delay(err_msg: str, default: float = 15.0) -> float:
    """Extracts suggested retry delay from Gemini 429 response if present."""
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_msg, re.IGNORECASE)
    if match:
        return min(float(match.group(1)) + 1.0, 60.0)
    return default


def generate_json(
    prompt: str,
    response_schema: dict[str, Any],
    system_instruction: str | None = None,
    audio_path: Path | None = None,
    max_retries: int = 3,
) -> Any:
    """Calls Gemini with global Redis rate-limiting and parses constrained JSON."""
    client = get_client()

    contents: list[Any] = []
    if audio_path is not None:
        mime_type, _ = mimetypes.guess_type(str(audio_path))
        audio_bytes = audio_path.read_bytes()
        contents.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime_type or "audio/mpeg"))
    contents.append(prompt)

    model = settings.GEMINI_TEXT_MODEL if audio_path is None else settings.GEMINI_AUDIO_MODEL

    for attempt in range(max_retries):
        try:
            # Shared Redis rate limiter check across all distributed Celery workers
            gemini_rate_limiter.acquire(timeout=45.0)

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.2,
                ),
            )
            return json.loads(response.text)
        except ClientError as exc:
            err_text = str(exc)
            if "429" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                delay = _extract_retry_delay(err_text, default=10.0 * (attempt + 1))
                if attempt < max_retries - 1:
                    logger.warning(
                        "Gemini Rate Limit (429). Throttling for %.1fs before retry %d/%d...",
                        delay,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(delay)
                    continue
                # Raise RateLimitError to trigger Celery exponential backoff with jitter
                raise RateLimitError(err_text, retry_after=delay) from exc
            raise
        except RateLimitError:
            raise
        except Exception as exc:
            if attempt < max_retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise


def generate_text(prompt: str, system_instruction: str | None = None, max_retries: int = 3) -> str:
    client = get_client()
    for attempt in range(max_retries):
        try:
            gemini_rate_limiter.acquire(timeout=45.0)
            response = client.models.generate_content(
                model=settings.GEMINI_TEXT_MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3),
            )
            return response.text or ""
        except ClientError as exc:
            err_text = str(exc)
            if "429" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                delay = _extract_retry_delay(err_text, default=10.0 * (attempt + 1))
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                raise RateLimitError(err_text, retry_after=delay) from exc
            raise
        except RateLimitError:
            raise
    return ""


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    if settings.USE_LOCAL_EMBEDDINGS:
        from app.services.embedding_service import generate_local_embedding

        return generate_local_embedding(text)

    client = get_client()
    try:
        gemini_rate_limiter.acquire(timeout=30.0)
        response = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=[text],
            config=types.EmbedContentConfig(task_type=task_type),
        )
        return list(response.embeddings[0].values)
    except Exception as exc:
        logger.warning("Embed single text fallback to local embedding: %s", exc)
        from app.services.embedding_service import generate_local_embedding

        return generate_local_embedding(text)


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT", max_retries: int = 2) -> list[list[float]]:
    if not texts:
        return []

    if settings.USE_LOCAL_EMBEDDINGS:
        from app.services.embedding_service import generate_local_embeddings_batch

        return generate_local_embeddings_batch(texts)

    client = get_client()
    all_embeddings: list[list[float]] = []
    chunk_size = 10

    for i in range(0, len(texts), chunk_size):
        chunk = texts[i : i + chunk_size]
        success = False
        for attempt in range(max_retries):
            try:
                gemini_rate_limiter.acquire(timeout=30.0)
                response = client.models.embed_content(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    contents=chunk,
                    config=types.EmbedContentConfig(task_type=task_type),
                )
                all_embeddings.extend([list(e.values) for e in response.embeddings])
                success = True
                break
            except Exception as exc:
                err_text = str(exc)
                if ("429" in err_text or "RESOURCE_EXHAUSTED" in err_text) and attempt < max_retries - 1:
                    time.sleep(5.0)
                    continue
                logger.warning("Embed chunk fallback to local embeddings: %s", exc)
                from app.services.embedding_service import generate_local_embeddings_batch

                all_embeddings.extend(generate_local_embeddings_batch(chunk))
                success = True
                break
        if not success:
            from app.services.embedding_service import generate_local_embeddings_batch

            all_embeddings.extend(generate_local_embeddings_batch(chunk))

    return all_embeddings

