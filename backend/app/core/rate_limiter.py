import logging
import time
import uuid
from typing import Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when the shared global rate limit is reached or Gemini returns 429."""

    def __init__(self, message: str = "Rate limit reached", retry_after: float = 15.0):
        super().__init__(message)
        self.retry_after = retry_after


class RedisGlobalRateLimiter:
    """Distributed token-bucket / sliding-window rate limiter backed by Redis.

    Ensures all Celery workers across any number of nodes coordinate
    globally and never exceed the Gemini Free Tier / API limits.
    """

    def __init__(
        self,
        redis_url: str = settings.REDIS_URL,
        key_prefix: str = "gemini:ratelimit",
        max_requests: int = settings.GEMINI_RPM_LIMIT,
        window_seconds: int = 60,

    ):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis_client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._redis_client is None:
            self._redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis_client

    def acquire(self, timeout: float = 30.0, max_requests: Optional[int] = None) -> bool:
        """Acquires permission to make an API call within the distributed window.

        Blocks briefly if the window is currently full. If timeout is exceeded,
        raises RateLimitError to trigger Celery exponential backoff with jitter.
        """
        limit = max_requests or self.max_requests
        start_time = time.time()
        redis_key = f"{self.key_prefix}:sliding_window"

        while True:
            try:
                now = time.time()
                window_start = now - self.window_seconds
                req_id = f"{now}:{uuid.uuid4().hex[:8]}"

                # Use a pipeline for atomic sliding-window operations
                pipe = self.client.pipeline()
                pipe.zremrangebyscore(redis_key, 0, window_start)
                pipe.zcard(redis_key)
                pipe.expire(redis_key, self.window_seconds + 5)
                results = pipe.execute()
                current_count = results[1]

                if current_count < limit:
                    # Slot available: register current timestamp and proceed
                    self.client.zadd(redis_key, {req_id: now})
                    self.client.expire(redis_key, self.window_seconds + 5)
                    return True

                # Window full: calculate how long until the oldest call in the window expires
                oldest_records = self.client.zrange(redis_key, 0, 0, withscores=True)
                if oldest_records:
                    oldest_time = oldest_records[0][1]
                    sleep_duration = max(0.5, (oldest_time + self.window_seconds) - now + 0.1)
                else:
                    sleep_duration = 1.0

                elapsed = time.time() - start_time
                if elapsed + sleep_duration > timeout:
                    logger.warning(
                        "Global rate limiter timeout (%.1fs elapsed). Raising RateLimitError for Celery backoff retry.",
                        elapsed,
                    )
                    raise RateLimitError(
                        f"Global rate limit of {limit} req/{self.window_seconds}s reached across workers.",
                        retry_after=sleep_duration,
                    )

                logger.info(
                    "Global rate limit reached (%d/%d). Throttling for %.2fs before retrying slot...",
                    current_count,
                    limit,
                    sleep_duration,
                )
                time.sleep(sleep_duration)

            except redis.RedisError as r_err:
                logger.warning("Redis rate limiter unavailable (%s). Falling back gracefully.", r_err)
                return True
            except RateLimitError:
                raise


# Global shared singleton
gemini_rate_limiter = RedisGlobalRateLimiter()
