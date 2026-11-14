import json
import logging
from typing import Any, Optional
from app.core.redis import get_async_redis

logger = logging.getLogger(__name__)
REDIS_NAMESPACE = "lvovo"  # all keys prefixed to avoid collisions

def make_key(key: str) -> str:
    """Namespace Redis keys to avoid collisions."""
    return f"{REDIS_NAMESPACE}:{key}"


async def get_cache(key: str) -> Optional[Any]:
    """
    Retrieve a JSON-serializable value from Redis.
    Returns None if key does not exist.
    """
    redis = await get_async_redis()
    namespaced_key = make_key(key)
    try:
        cached = await redis.get(namespaced_key)
        if cached is not None:
            return json.loads(cached)
    except Exception as e:
        logger.error(f"Failed to get cache for key={key}: {e}")
    return None


async def set_cache(key: str, value: Any, ttl: int = 60) -> None:
    """
    Store JSON-serializable data in Redis with a TTL (seconds).
    """
    redis = await get_async_redis()
    namespaced_key = make_key(key)
    try:
        # default=str: prices are Decimals and dates are datetimes; both go out as strings anyway
        await redis.setex(namespaced_key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.error(f"Failed to set cache for key={key}: {e}")


async def delete_cache(key: str) -> None:
    """Remove a key from Redis."""
    redis = await get_async_redis()
    namespaced_key = make_key(key)
    try:
        await redis.delete(namespaced_key)
    except Exception as e:
        logger.error(f"Failed to delete cache for key={key}: {e}")
