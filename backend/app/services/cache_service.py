"""
Cache Service - Redis-based caching for expensive queries.

Features:
- Async Redis operations
- Automatic serialization/deserialization
- TTL-based expiration
- Cache key generation
- Cache invalidation patterns
"""

import hashlib
import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, TypeVar

from app.core.config import settings
from app.schemas.common import CacheControl
from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheService:
    """
    Production-ready cache service using Redis.

    Features:
    - Async operations
    - JSON serialization
    - Automatic TTL management
    - Cache key prefixing
    - Stats tracking
    """

    # Default TTL values (in seconds)
    TTL_SHORT = 60  # 1 minute - for real-time data
    TTL_MEDIUM = 300  # 5 minutes - for search results
    TTL_LONG = 3600  # 1 hour - for static data
    TTL_VERY_LONG = 86400  # 24 hours - for rarely changing data

    # Key prefixes
    PREFIX_SEARCH = "search:"
    PREFIX_QUOTE = "quote:"
    PREFIX_STATIC = "static:"
    PREFIX_USER = "user:"

    def __init__(self):
        self.enabled = bool(settings.REDIS_URL)
        if not self.enabled:
            logger.warning("Cache disabled: REDIS_URL not configured")

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled:
            return None

        try:
            redis = await get_redis()
            value = await redis.get(key)

            if value is None:
                logger.debug(f"Cache MISS: {key}")
                return None

            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)

        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = TTL_MEDIUM) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            redis = await get_redis()
            serialized = json.dumps(value, default=str)
            await redis.setex(key, ttl_seconds, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self.enabled:
            return False

        try:
            redis = await get_redis()
            await redis.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True

        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis glob pattern (e.g., "search:flights:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            redis = await get_redis()
            keys = await redis.keys(pattern)

            if keys:
                await redis.delete(*keys)
                logger.debug(f"Cache DELETE PATTERN: {pattern} ({len(keys)} keys)")
                return len(keys)

            return 0

        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    async def get_or_set(
        self, key: str, factory: Callable[[], Any], ttl_seconds: int = TTL_MEDIUM
    ) -> tuple[Any, CacheControl]:
        """
        Get value from cache or compute and store it.

        Args:
            key: Cache key
            factory: Async function to compute value if not cached
            ttl_seconds: Time to live in seconds

        Returns:
            Tuple of (value, cache_control)
        """
        # Try to get from cache first
        cached_value = await self.get(key)

        if cached_value is not None:
            # Return cached value with metadata
            return cached_value, CacheControl(cached=True, cache_key=key, ttl_seconds=ttl_seconds)

        # Compute value
        if callable(factory):
            value = await factory() if hasattr(factory, "__await__") else factory()
        else:
            value = factory

        # Store in cache
        await self.set(key, value, ttl_seconds)

        return value, CacheControl(
            cached=False,
            cache_key=key,
            ttl_seconds=ttl_seconds,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        )

    @staticmethod
    def generate_key(*args, prefix: str = "") -> str:
        """
        Generate a cache key from arguments.

        Args:
            *args: Values to include in key
            prefix: Key prefix

        Returns:
            Hashed cache key
        """
        # Convert all args to strings and join
        key_data = ":".join(str(arg) for arg in args)

        # Hash for consistent, safe key length
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]

        return f"{prefix}{key_hash}"

    @staticmethod
    def flight_search_key(
        origin: str, destination: str, date: str, passengers: int, cabin: str, page: int = 1
    ) -> str:
        """Generate cache key for flight search."""
        return CacheService.generate_key(
            origin,
            destination,
            date,
            passengers,
            cabin,
            page,
            prefix=CacheService.PREFIX_SEARCH + "flights:",
        )

    @staticmethod
    def hotel_search_key(
        city: str, checkin: str, checkout: str, guests: int, rooms: int, page: int = 1
    ) -> str:
        """Generate cache key for hotel search."""
        return CacheService.generate_key(
            city,
            checkin,
            checkout,
            guests,
            rooms,
            page,
            prefix=CacheService.PREFIX_SEARCH + "hotels:",
        )

    @staticmethod
    def airport_search_key(query: str) -> str:
        """Generate cache key for airport search."""
        return f"{CacheService.PREFIX_STATIC}airports:{query.lower()}"

    @staticmethod
    def station_search_key(query: str) -> str:
        """Generate cache key for train station search."""
        return f"{CacheService.PREFIX_STATIC}stations:{query.lower()}"


# Singleton instance
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Get or create the cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# ==================== Decorator for caching ====================


def cached(
    key_prefix: str,
    ttl_seconds: int = CacheService.TTL_MEDIUM,
    key_builder: Callable[..., str] | None = None,
):
    """
    Decorator to cache async function results.

    Usage:
        @cached("flights", ttl_seconds=300)
        async def search_flights(origin, destination, date):
            ...

    Args:
        key_prefix: Prefix for cache key
        ttl_seconds: Cache TTL
        key_builder: Optional function to build custom cache key
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = get_cache_service()

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: hash all arguments
                key_data = f"{func.__name__}:{args}:{kwargs}"
                cache_key = CacheService.generate_key(key_data, prefix=key_prefix)

            # Try cache first
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator
