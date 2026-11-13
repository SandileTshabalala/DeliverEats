import asyncio
import json
from typing import Dict, Iterable, Optional, Set

from fastapi import WebSocket


class ConnectionManager:
    """
    Tracks open order-update sockets per user.

    Events are delivered only to the people involved in an order (customer,
    restaurant owner, driver) plus platform admins, never to everybody.

    Most route handlers are plain `def` functions, which FastAPI runs in a worker
    thread where there is no event loop. `notify()` is therefore thread-safe: it
    hands the send over to the server's main loop, captured at startup.
    """

    def __init__(self):
        self.connections: Dict[WebSocket, dict] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def register(self, websocket: WebSocket, user_id: str, role: str) -> None:
        """Call after the socket has been accepted and the user authenticated."""
        self.connections[websocket] = {"user_id": user_id, "role": role}

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.pop(websocket, None)

    async def send_to_users(self, message: dict, user_ids: Iterable[str], include_admins: bool = True) -> None:
        targets: Set[str] = {uid for uid in user_ids if uid}
        payload = json.dumps(message, default=str)
        stale = []
        for websocket, info in list(self.connections.items()):
            is_admin = info["role"] in ("super_admin", "admin")
            if info["user_id"] not in targets and not (include_admins and is_admin):
                continue
            try:
                await websocket.send_text(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)

    def notify(self, message: dict, user_ids: Iterable[str], include_admins: bool = True) -> None:
        """Fire-and-forget delivery that works from sync (threadpool) and async code."""
        user_ids = list(user_ids)
        if not self.connections:
            return
        coro = self.send_to_users(message, user_ids, include_admins)
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is not None:
            running.create_task(coro)
        elif self.loop is not None and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self.loop)
        else:
            coro.close()  # no loop available (e.g. Celery worker): nothing to deliver to


manager = ConnectionManager()
