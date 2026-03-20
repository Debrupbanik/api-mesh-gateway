"""Rate limiter implementation using sliding window algorithm."""

import asyncio
import time
from typing import Optional, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_requests: int = 100
    window_seconds: int = 60
    burst_size: Optional[int] = None


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.

    Uses a sliding window algorithm to track requests per client.
    More accurate than fixed window, prevents burst at window boundaries.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._requests: Dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    def _cleanup_old_requests(self, client_id: str, current_time: float):
        """Remove requests outside the sliding window."""
        if client_id in self._requests:
            cutoff = current_time - self.config.window_seconds
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > cutoff
            ]

    async def is_allowed(self, client_id: str) -> tuple[bool, dict]:
        """
        Check if request is allowed for the client.

        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        async with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(client_id, current_time)

            if client_id not in self._requests:
                self._requests[client_id] = []

            request_count = len(self._requests[client_id])
            max_requests = self.config.max_requests

            if self.config.burst_size and request_count >= self.config.burst_size:
                return False, self._get_info(client_id, current_time)

            if request_count >= max_requests:
                return False, self._get_info(client_id, current_time)

            self._requests[client_id].append(current_time)
            return True, self._get_info(client_id, current_time)

    def _get_info(self, client_id: str, current_time: float) -> dict:
        """Get rate limit info for client."""
        if client_id not in self._requests:
            remaining = self.config.max_requests
            reset_at = current_time + self.config.window_seconds
        else:
            remaining = max(
                0, self.config.max_requests - len(self._requests[client_id])
            )
            if self._requests[client_id]:
                oldest = min(self._requests[client_id])
                reset_at = oldest + self.config.window_seconds
            else:
                reset_at = current_time + self.config.window_seconds

        return {
            "limit": self.config.max_requests,
            "remaining": remaining,
            "reset_at": int(reset_at),
            "retry_after": max(0, int(reset_at - current_time)),
        }

    async def get_client_usage(self, client_id: str) -> int:
        """Get current request count for a client."""
        async with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(client_id, current_time)
            return len(self._requests.get(client_id, []))

    async def reset_client(self, client_id: str):
        """Reset rate limit for a client."""
        async with self._lock:
            if client_id in self._requests:
                del self._requests[client_id]


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.

    Allows burst traffic up to bucket size, then refills at steady rate.
    """

    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self._buckets: Dict[str, tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_id: str, tokens: int = 1) -> tuple[bool, dict]:
        """Check if request is allowed."""
        async with self._lock:
            current_time = time.time()

            if client_id not in self._buckets:
                self._buckets[client_id] = (float(self.capacity), current_time)

            tokens_available, last_update = self._buckets[client_id]

            elapsed = current_time - last_update
            tokens_available = min(
                self.capacity, tokens_available + elapsed * self.rate
            )

            if tokens_available >= tokens:
                tokens_available -= tokens
                self._buckets[client_id] = (tokens_available, current_time)
                allowed = True
            else:
                self._buckets[client_id] = (tokens_available, current_time)
                allowed = False

            retry_after = (tokens - tokens_available) / self.rate if not allowed else 0

            return allowed, {
                "limit": self.capacity,
                "remaining": int(tokens_available),
                "reset_at": int(
                    current_time + (self.capacity - tokens_available) / self.rate
                ),
                "retry_after": max(0, int(retry_after)),
            }


class RateLimiterManager:
    """Manages multiple rate limiters for different routes/services."""

    def __init__(self):
        self._limiters: Dict[str, SlidingWindowRateLimiter] = {}
        self._lock = asyncio.Lock()

    async def get_limiter(
        self, name: str, config: Optional[RateLimitConfig] = None
    ) -> SlidingWindowRateLimiter:
        """Get or create a rate limiter."""
        async with self._lock:
            if name not in self._limiters:
                self._limiters[name] = SlidingWindowRateLimiter(config)
            return self._limiters[name]

    async def check_rate_limit(self, route: str, client_id: str) -> tuple[bool, dict]:
        """Check rate limit for a route and client."""
        limiter = await self.get_limiter(route)
        return await limiter.is_allowed(client_id)
