"""
In-app notifications (the bell in the header).

Kept in Redis rather than the database: they are short-lived, read constantly,
and Redis sits next to the API, so the bell costs nothing even when the
database is far away. Each user keeps their latest 50 for 30 days.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.core import redis as redis_module

MAX_ITEMS = 50
TTL_SECONDS = 60 * 60 * 24 * 30


def _list_key(user_id: str) -> str:
    return f"lvovo:inbox:{user_id}"


def _unread_key(user_id: str) -> str:
    return f"lvovo:inbox_unread:{user_id}"


def add(user_id: str, title: str, message: str, link: Optional[str] = None) -> None:
    """Never raises: a notification must not break the action that caused it."""
    try:
        client = redis_module.redis_client
        item = {
            "id": uuid.uuid4().hex,
            "title": title,
            "message": message,
            "link": link,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client.lpush(_list_key(user_id), json.dumps(item))
        client.ltrim(_list_key(user_id), 0, MAX_ITEMS - 1)
        client.expire(_list_key(user_id), TTL_SECONDS)
        client.incr(_unread_key(user_id))
        client.expire(_unread_key(user_id), TTL_SECONDS)
    except Exception:
        pass


def read(user_id: str) -> dict:
    try:
        client = redis_module.redis_client
        raw: List = client.lrange(_list_key(user_id), 0, MAX_ITEMS - 1)
        unread = int(client.get(_unread_key(user_id)) or 0)
    except Exception:
        return {"unread": 0, "items": []}
    items = []
    for entry in raw:
        try:
            items.append(json.loads(entry))
        except (TypeError, ValueError):
            continue
    return {"unread": min(unread, len(items)), "items": items}


def mark_read(user_id: str) -> None:
    try:
        redis_module.redis_client.delete(_unread_key(user_id))
    except Exception:
        pass
