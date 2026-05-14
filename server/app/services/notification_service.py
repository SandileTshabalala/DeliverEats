from typing import Literal
import redis
from app.core.redis import redis_client

# Placeholder for actual integrations: push, email, SMS
def send_notification(user_id: str, title: str, message: str, channel: Literal["push","email","sms"]="push"):
    """
    Send notification to a user. Currently logs + optional Redis queue.
    """
    # Redis queue for async worker (Celery, RQ)
    redis_client.rpush("notifications_queue", str({
        "user_id": user_id,
        "title": title,
        "message": message,
        "channel": channel
    }))

    print(f"[NOTIFY] {channel.upper()} {user_id}: {title} - {message}")
