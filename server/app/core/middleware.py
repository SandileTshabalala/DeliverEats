import uuid
from starlette.types import ASGIApp, Scope, Receive, Send
from app.core.locger import logger
from datetime import datetime, timezone 

# --- Middleware ---
# --- Middleware ---
class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode()
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in scope for other middlewares/routes
        scope["request_id"] = request_id

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add header to response
                headers = list(message.get("headers", []))
                headers.append((b"X-Request-ID", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = scope.get("request_id", "unknown")
        method = scope.get("method", "WS")
        path = scope.get("path", "")
        client_host = scope.get("client", [None])[0]

        logger.info(
            "Request received",
            extra={
                "req_id": request_id,
                "method": method,
                "url": path,
                "client": client_host,
            },
        )

        start_time = datetime.now(timezone.utc)

        async def send_wrapper(message):
            if message["type"] in ("http.response.start", "websocket.accept"):
                # Handle start of response
                pass
            
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                process_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                logger.info(
                    "Request completed",
                    extra={
                        "req_id": request_id,
                        "status_code": status_code,
                        "process_time_ms": f"{process_time:.2f}",
                    },
                )
            
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            process_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(
                "Request failed",
                extra={
                    "req_id": request_id,
                    "error": str(e),
                    "process_time_ms": f"{process_time:.2f}",
                },
                exc_info=True,
            )
            raise

