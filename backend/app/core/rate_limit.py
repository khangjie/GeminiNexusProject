from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings


@dataclass
class RateLimitPolicy:
    requests_per_minute: int


class InMemoryRateLimiter:
    """Simple per-key fixed-window limiter using in-memory timestamp queues."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, max_requests: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            queue = self._events[key]
            while queue and (now - queue[0]) > window_seconds:
                queue.popleft()

            if len(queue) >= max_requests:
                retry_after = int(window_seconds - (now - queue[0])) if queue else window_seconds
                return False, max(1, retry_after)

            queue.append(now)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API-level rate limiting with stricter limits on expensive AI endpoints."""

    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self.limiter = InMemoryRateLimiter()
        self.ai_paths = {
            "/api/v1/receipts/upload",
            "/api/v1/analytics/query",
        }

    def _client_key(self, request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"
        return f"{client_ip}:{request.url.path}"

    def _policy_for(self, request: Request) -> RateLimitPolicy:
        if request.url.path in self.ai_paths:
            return RateLimitPolicy(requests_per_minute=self.settings.RATE_LIMIT_AI_REQUESTS_PER_MINUTE)
        return RateLimitPolicy(requests_per_minute=self.settings.RATE_LIMIT_REQUESTS_PER_MINUTE)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        if not self.settings.ENABLE_RATE_LIMIT or not request.url.path.startswith("/api/"):
            return await call_next(request)

        policy = self._policy_for(request)
        allowed, retry_after = self.limiter.allow(
            key=self._client_key(request),
            max_requests=policy.requests_per_minute,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
