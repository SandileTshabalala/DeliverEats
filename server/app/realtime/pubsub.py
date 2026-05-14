import json
import asyncio
from app.core.redis import redis_client
from app.realtime.connection_manager import manager

CHANNEL = "realtime-events"

async def publish_event(event: dict):
    await redis_client.publish(CHANNEL, json.dumps(event))

async def listen_events():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL)

    async for message in pubsub.listen():
        if message["type"] == "message":
            event = json.loads(message["data"])
            await manager.send_personal(
                event["user_id"],
                event
            )
