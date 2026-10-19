"""In-memory sliding window rate limiter for ConversionBridge endpoints."""

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from ..config import settings


class RateLimiter:
    """Thread-safe sliding-window rate limiter per client identifier."""

    def __init__(self, requests_per_minute: int = 120):
        self.limit = requests_per_minute
        self.window_seconds = 60
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Check whether the key has exceeded its allowed quota in the sliding window.

        Raises HTTPException(429) if exceeded.
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Filter out entries outside the sliding window
            self._history[key] = [t for t in self._history[key] if t > window_start]

            if len(self._history[key]) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit of {self.limit} requests/minute exceeded. Please retry later.",
                    headers={"Retry-After": "60"},
                )

            self._history[key].append(now)

    def reset(self) -> None:
        """Clear all rate limiting history (useful for test resets)."""
        with self._lock:
            self._history.clear()


# Global rate limiter instance configured from settings
rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)


async def check_rate_limit(request: Request) -> None:
    """FastAPI dependency to enforce rate limits on incoming HTTP requests."""
    # Determine client identifier: API key header if present, otherwise client host IP
    client_id = request.headers.get("X-API-Key") or (
        request.client.host if request.client else "unknown-client"
    )
    rate_limiter.check(client_id)
