from fastapi import APIRouter, WebSocket, Depends
from app.realtime.connection_manager import manager
from app.core.security import get_current_user_ws

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user = Depends(get_current_user_ws),
):
    user_id = str(user.id)

    await manager.connect(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except Exception:
        manager.disconnect(user_id, websocket)
