"""In-memory rate limiter middleware."""

import time
from collections import defaultdict
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst: int = 10,
    ):
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.burst = burst
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": burst, "last": time.monotonic()}
        )

    def _refill(self, key: str) -> None:
        bucket = self._buckets[key]
        now = time.monotonic()
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rate)
        bucket["last"] = now

    def allow(self, key: str) -> bool:
        """Check if request is allowed."""
        self._refill(key)
        bucket = self._buckets[key]
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False

    def remaining(self, key: str) -> int:
        """Get remaining tokens for a key."""
        self._refill(key)
        return max(0, int(self._buckets[key]["tokens"]))

    def reset(self, key: Optional[str] = None) -> None:
        """Reset rate limit for a key or all keys."""
        if key:
            if key in self._buckets:
                del self._buckets[key]
        else:
            self._buckets.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        burst: int = 20,
        key_func=None,
    ):
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute, burst)
        self.key_func = key_func or self._default_key

    @staticmethod
    def _default_key(request: Request) -> str:
        """Default: use client IP as rate limit key."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip health check
        if request.url.path == "/health":
            return await call_next(request)

        key = self.key_func(request)
        if not self.limiter.allow(key):
            remaining = self.limiter.remaining(key)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "remaining": remaining,
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(self.limiter.remaining(key))
        return response
