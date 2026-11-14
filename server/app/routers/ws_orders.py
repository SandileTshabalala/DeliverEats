import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.redis import get_async_redis
from app.core.roles import Role
from app.core.security import is_token_blacklisted, issued_before_password_change
from app.db.session import SessionLocal
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.models.user import User
from app.services.driver_service import update_driver_location
from app.utils.OrderStatus import OrderStatus
from app.utils.websocket_manager import manager

router = APIRouter(tags=["WebSocket Orders"])

DRIVER_LOCATION_CHANNEL = "driver_locations"
# Persisting every GPS ping would hammer the database: save at most this often
LOCATION_SAVE_INTERVAL_SECONDS = 15


def _load_user(user_id: str) -> Optional[dict]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            return None
        return {"id": user.id, "email": user.email, "role": user.role.value}
    finally:
        db.close()


async def authenticate(websocket: WebSocket) -> Optional[dict]:
    """
    Accept the socket and identify the user from `?token=<access token>`.
    Browsers cannot set headers on WebSockets, hence the query parameter.
    Returns None (after closing the socket) when the token is not valid.
    """
    await websocket.accept()
    token = websocket.query_params.get("token")
    user = None
    if token:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if (payload.get("type") == "access" and payload.get("sub")
                    and not await is_token_blacklisted(token)
                    and not issued_before_password_change(payload)):
                user = await run_in_threadpool(_load_user, payload["sub"])
        except JWTError:
            user = None

    if not user:
        try:
            await websocket.send_text(json.dumps({"type": "auth_error", "detail": "Not authenticated"}))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass
        return None
    return user


@router.websocket("/updates")
async def order_updates_ws(websocket: WebSocket):
    """Order status events for the signed-in user (only orders they are part of)."""
    user = await authenticate(websocket)
    if not user:
        return

    manager.register(websocket, user["id"], user["role"])
    try:
        await websocket.send_text(json.dumps({
            "type": "auth_success",
            "user": user["email"],
            "message": "Connected to order updates"
        }))
        while True:
            await websocket.receive_text()  # keep the connection open
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        manager.disconnect(websocket)


@router.websocket("/driver/{driver_id}")
async def driver_location_ws(websocket: WebSocket, driver_id: str):
    """A driver streams their own GPS position: {"lat": .., "lng": .., "ts": ..}."""
    user = await authenticate(websocket)
    if not user:
        return
    if user["role"] != Role.DRIVER.value or user["id"] != driver_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    redis = await get_async_redis()
    last_saved = 0.0
    try:
        while True:
            try:
                payload = json.loads(await websocket.receive_text())
                lat, lng = float(payload["lat"]), float(payload["lng"])
            except (ValueError, KeyError, TypeError):
                continue  # ignore malformed messages instead of dropping the driver
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue

            location = {"driver_id": driver_id, "lat": lat, "lng": lng, "ts": payload.get("ts")}
            await redis.set(f"driver:{driver_id}:location", json.dumps(location), ex=300)
            await redis.publish(DRIVER_LOCATION_CHANNEL, json.dumps(location))

            now = asyncio.get_running_loop().time()
            if now - last_saved >= LOCATION_SAVE_INTERVAL_SECONDS:
                last_saved = now
                await run_in_threadpool(_save_location, driver_id, lat, lng)
    except (WebSocketDisconnect, RuntimeError):
        pass


def _save_location(driver_id: str, lat: float, lng: float) -> None:
    db = SessionLocal()
    try:
        update_driver_location(db, driver_id, lat, lng)
    finally:
        db.close()


def _tracking_driver_id(order_id: str, user: dict) -> Optional[str]:
    """Driver to follow for this order, or None if the user may not track it."""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or not order.driver_id:
            return None
        if order.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            return None
        allowed = user["role"] in (Role.SUPER_ADMIN.value, Role.ADMIN.value) or user["id"] == order.customer_id
        if not allowed and user["role"] == Role.RESTAURANT_ADMIN.value:
            from app.core.tenancy import restaurant_member_ids
            restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
            allowed = restaurant is not None and user["id"] in restaurant_member_ids(db, restaurant)
        return order.driver_id if allowed else None
    finally:
        db.close()


@router.websocket("/order/{order_id}")
async def order_tracking_ws(websocket: WebSocket, order_id: str):
    """Live position of the driver delivering one order, for the people on that order."""
    user = await authenticate(websocket)
    if not user:
        return

    driver_id = await run_in_threadpool(_tracking_driver_id, order_id, user)
    if not driver_id:
        await websocket.send_text(json.dumps({"type": "tracking_unavailable"}))
        await websocket.close()
        return

    redis = await get_async_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(DRIVER_LOCATION_CHANNEL)

    async def forward_locations():
        last_known = await redis.get(f"driver:{driver_id}:location")
        if last_known:
            await websocket.send_text(last_known)
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except (asyncio.TimeoutError, TimeoutError):
                continue
            if not message:
                continue
            data = message["data"]
            # Only this order's driver: never leak other drivers' positions
            if json.loads(data).get("driver_id") == driver_id:
                await websocket.send_text(data)

    forwarder = asyncio.create_task(forward_locations())
    try:
        while True:
            await websocket.receive_text()  # returns/raises when the client leaves
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        forwarder.cancel()
        try:
            await pubsub.unsubscribe(DRIVER_LOCATION_CHANNEL)
            close = getattr(pubsub, "aclose", None) or pubsub.close
            await close()
        except Exception:
            pass
