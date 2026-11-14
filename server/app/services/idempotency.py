"""
Run a request once per Idempotency-Key. Used for placing orders: a phone on a
weak signal may send the same "place order" twice, and the kitchen must not
get two orders.

    with idempotency.once(scope, key) as previous:
        if previous: return the earlier result (looked up by its id)
        ...do the work...
        idempotency.remember(scope, key, result_id)

Keys live in Redis for 24 hours. Without a key, or when Redis is down, the
request simply runs (the app's own double-tap guard still applies).
"""
from contextlib import contextmanager
from typing import Iterator, Optional

from fastapi import HTTPException

from app.core.locger import logger

TTL_SECONDS = 24 * 3600
_IN_PROGRESS = "__in_progress__"


def _key(scope: str, key: str) -> str:
    return f"lvovo:idem:{scope}:{key}"


def _redis():
    from app.core.redis import redis_client
    return redis_client


@contextmanager
def once(scope: str, key: Optional[str]) -> Iterator[Optional[str]]:
    """Yields the id remembered for this key (a repeat), or None the first time."""
    if not key:
        yield None
        return
    name = _key(scope, key)
    try:
        claimed = _redis().set(name, _IN_PROGRESS, nx=True, ex=TTL_SECONDS)
        previous = None if claimed else _redis().get(name)
    except Exception as exc:
        logger.warning(f"idempotency: Redis unavailable ({exc}); running the request anyway")
        yield None
        return
    if isinstance(previous, bytes):
        previous = previous.decode()
    if previous == _IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Your order is already being placed. Please wait a moment.")
    if previous:
        yield previous
        return
    try:
        yield None
    except BaseException:
        # it failed: let the customer try again with the same key
        try:
            _redis().delete(name)
        except Exception:
            pass
        raise


def remember(scope: str, key: Optional[str], result_id: str) -> None:
    if not key:
        return
    try:
        _redis().set(_key(scope, key), result_id, ex=TTL_SECONDS)
    except Exception:
        pass
