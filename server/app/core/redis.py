import logging
import redis
from redis.exceptions import RedisError
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool as AsyncConnectionPool
from redis.connection import ConnectionPool as SyncConnectionPool
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Connection pools (singletons)
# ─────────────────────────────────────────────────────────────

_sync_pool: Optional[SyncConnectionPool] = None
_async_pool: Optional[AsyncConnectionPool] = None

 
# ─────────────────────────────────────────────────────────────
# Sync Redis (for background jobs / celery / migrations)
# ─────────────────────────────────────────────────────────────

_sync_pool = None

def get_sync_redis() -> redis.Redis:
    global _sync_pool

    if _sync_pool is None:
        try:
            _sync_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=getattr(settings, "REDIS_MAX_CONNECTIONS", 10),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            logger.info("Sync Redis pool initialized")
        except RedisError as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
            raise

    return redis.Redis(connection_pool=_sync_pool)


# ─────────────────────────────────────────────────────────────
# Async Redis (FastAPI / rate limiting / caching)
# ─────────────────────────────────────────────────────────────

async def get_async_redis() -> Redis:
    global _async_pool

    if _async_pool is None:
        _async_pool = AsyncConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        logger.info("Async Redis pool initialized")

    return Redis(connection_pool=_async_pool)


# ─────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────

async def check_redis_health() -> bool:
    try:
        redis = await get_async_redis()
        await redis.ping()
        return True
    except Exception as e:
        logger.error("Redis health check failed", exc_info=e)
        return False


# ─────────────────────────────────────────────────────────────
# Graceful shutdown
# ─────────────────────────────────────────────────────────────

async def close_redis_connections():
    global _sync_pool, _async_pool

    if _sync_pool:
        try:
            _sync_pool.disconnect()
            logger.info("Sync Redis pool closed")
        except Exception as e:
            logger.error("Failed to close sync Redis pool", exc_info=e)
        finally:
            _sync_pool = None

    if _async_pool:
        try:
            await _async_pool.disconnect()
            logger.info("Async Redis pool closed")
        except Exception as e:
            logger.error("Failed to close async Redis pool", exc_info=e)
        finally:
            _async_pool = None


# ─────────────────────────────────────────────────────────────
# Backwards compatibility (DO NOT use in async code)
# ─────────────────────────────────────────────────────────────

redis_client = get_sync_redis()
