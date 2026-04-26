import time

import redis

from app.config import settings

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, user_id: str) -> tuple[bool, int, int]:
        client = get_redis_client()
        key = f"rate_limit:{user_id}"
        now = time.time()
        window_start = now - self.window_seconds

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, self.window_seconds)
        results = pipe.execute()

        request_count = results[2]
        remaining = max(0, self.max_requests - request_count)
        allowed = request_count <= self.max_requests

        return allowed, remaining, request_count


rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_per_minute, window_seconds=60
)
