from fastapi import WebSocket
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
        except Exception as e:
            print(f"Failed to accept websocket: {e}")
            raise

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except (WebSocketDisconnect, RuntimeError):
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        stale_connections = []
        for connection in self.active_connections:
            try:
                # Use a timeout or check state if needed, but basic try-except handles most cases
                await connection.send_text(message)
            except (WebSocketDisconnect, RuntimeError):
                stale_connections.append(connection)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)

manager = ConnectionManager()
