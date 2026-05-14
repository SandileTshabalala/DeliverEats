from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from jose import JWTError, jwt
from app.utils.websocket_manager import manager
from app.core.config import settings
import json
import redis

r = redis.Redis()

router = APIRouter(tags=["WebSocket Orders"])

@router.websocket("/updates")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = None,
    db: Session = Depends(get_db)
):
    # Establish connection first
    try:
        await manager.connect(websocket)
    except Exception:
        # Acceptance failed (client disconnect or middleware error)
        return
    
    # If token wasn't in query params automatically, try finding it manually
    if not token:
        token = websocket.query_params.get("token")

    if not token:
        try:
            await websocket.send_text(json.dumps({"type": "auth_error", "detail": "No token provided"}))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except:
            pass
        manager.disconnect(websocket)
        return

    try:
        from app.core.security import get_current_user
        # Mock request for get_current_user
        class MockRequest:
            def __init__(self, token):
                self.headers = {"authorization": f"Bearer {token}"}
                self.state = type('state', (), {})()
                self.client = websocket.client
        
        mock_request = MockRequest(token)
        current_user = await get_current_user(mock_request, token, db)
        await websocket.send_text(json.dumps({
            "type": "auth_success", 
            "user": current_user.email,
            "message": "Connected to order updates"
        }))
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "auth_error", "detail": str(e)}))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except:
            pass
        manager.disconnect(websocket)
        return

    try:
        while True:
            # Keep connection alive and wait for messages
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        manager.disconnect(websocket)

active_drivers = {}

@router.websocket("/driver/{driver_id}")
async def driver_ws(websocket: WebSocket, driver_id: str):
    await websocket.accept()
    active_drivers[driver_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            location = {
                "lat": payload["lat"],
                "lng": payload["lng"],
                "ts": payload["ts"]
            }

            r.set(f"driver:{driver_id}:location", json.dumps(location))
            r.publish("driver_locations", json.dumps({
                "driver_id": driver_id,
                **location
            }))
    except WebSocketDisconnect:
        pass
    
@router.websocket("/order/{order_id}")
async def order_tracking_ws(websocket: WebSocket, order_id: str):
    await websocket.accept()
    pubsub = r.pubsub()
    pubsub.subscribe("driver_locations")

    for msg in pubsub.listen():
        if msg["type"] == "message":
            await websocket.send_text(msg["data"].decode())