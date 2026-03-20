"""Redis-based caching with AI-predicted TTL."""

import json
import hashlib
from typing import Optional, Any
import logging

import redis.asyncio as redis

from ..config import get_settings

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis-based cache manager with AI-predicted TTL support.

    Features:
    - Automatic cache invalidation
    - AI-predicted optimal TTL
    - Cache statistics tracking
    - Graceful degradation when Redis unavailable
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or get_settings().redis_url
        self.enabled = get_settings().redis_enabled
        self._client: Optional[redis.Redis] = None
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    async def connect(self):
        """Connect to Redis."""
        if not self.enabled:
            logger.info("Cache disabled")
            return

        try:
            self._client = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.enabled = False
            self._client = None

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"apimesh:{prefix}:{key_hash}"

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self.enabled or not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value:
                self._stats["hits"] += 1
            else:
                self._stats["misses"] += 1
            return value
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        """Set value in cache with TTL."""
        if not self.enabled or not self._client:
            return

        try:
            if ttl is None:
                ttl = get_settings().redis_ttl_default
            await self._client.setex(key, ttl, value)
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache set error: {e}")

    async def delete(self, key: str):
        """Delete value from cache."""
        if not self.enabled or not self._client:
            return

        try:
            await self._client.delete(key)
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache delete error: {e}")

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        if not self.enabled or not self._client:
            return

        try:
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(
                    cursor, match=f"apimesh:{pattern}", count=100
                )
                if keys:
                    await self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")

    async def get_or_set(self, key: str, fetch_func, ttl: Optional[int] = None) -> Any:
        """
        Get from cache or fetch and cache the result.

        Args:
            key: Cache key
            fetch_func: Async function to fetch data if not cached
            ttl: Time to live in seconds
        """
        cached = await self.get(key)
        if cached is not None:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                return cached

        result = await fetch_func()
        if result is not None:
            value = json.dumps(result) if not isinstance(result, str) else result
            await self.set(key, value, ttl)
        return result

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total * 100 if total > 0 else 0
        return {
            **self._stats,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
        }

    async def reset_stats(self):
        """Reset cache statistics."""
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
