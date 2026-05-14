import time
from functools import wraps
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from starlette.types import ASGIApp, Scope, Receive, Send
from app.core.redis import redis_client
from app.core.redis import get_async_redis
from app.core.config import settings
from app.core.config import settings
from app.core.locger import logger
import asyncio
from fastapi.concurrency import run_in_threadpool
from starlette.responses import Response

class RateLimitExceeded(HTTPException):
    """Custom exception for rate limiting with retry information."""
    def __init__(self, retry_after: int, limit: int, remaining: int = 0):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": retry_after,
                "limit": limit,
                "remaining": remaining
            }
        )
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining

class RateLimiter:
    """Enhanced rate limiter using token bucket algorithm."""
    
    def __init__(
        self,
        key_prefix: str,
        limit: int = 60,
        window: int = 60,
        user_based: bool = False,
        skip: bool = False
    ):
        self.key_prefix = key_prefix
        self.limit = limit
        self.window = window
        self.user_based = user_based
        self.skip = skip or settings.DEBUG  # Skip rate limiting in debug mode

    async def _get_identifier(self, request: Request) -> str:
        """Get rate limit identifier (IP or user ID)."""
        if self.user_based and request.user.is_authenticated:
            return f"user:{request.user.id}"
        return f"ip:{request.client.host}"

    async def _get_limits(self, request: Request) -> tuple[int, int]:
        """Get rate limits based on user role."""
        if self.user_based and request.user.is_authenticated:
            # Example: Different limits for different roles
            if request.user.role == "admin":
                return 1000, 60  # 1000 requests per minute for admins
            elif request.user.role == "premium":
                return 500, 60   # 500 requests per minute for premium users
        return self.limit, self.window

    async def _check_rate_limit(self, key: str, limit: int, window: int) -> dict:
        """Check rate limit using Redis with token bucket algorithm."""
        now = int(time.time())
        try:
            redis = await get_async_redis()
            async with redis.pipeline() as pipe:
                # Use Redis transactions for atomic operations
                pipe.multi()
                pipe.hgetall(key)
                pipe.hsetnx(key, "tokens", limit)
                pipe.hsetnx(key, "last_check", now)
                results = await pipe.execute()
                
            bucket = results[0] or {}
            tokens = int(bucket.get("tokens", limit))
            last_check = int(bucket.get("last_check", now))
            
            # Calculate tokens to add based on time passed
            time_passed = now - last_check
            refill_amount = (time_passed * limit) // window
            tokens = min(limit, tokens + refill_amount)
            
            # Check if request is allowed
            if tokens < 1:
                retry_after = (window // limit) + 1
                return {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "retry_after": retry_after
                }
            
            # Update token count and last check time
            await redis.hset(key, mapping={
                "tokens": tokens - 1,
                "last_check": now
            })
            await redis.expire(key, window * 2)  # Auto-cleanup
            
            return {
                "allowed": True,
                "limit": limit,
                "remaining": tokens - 1,
                "retry_after": 0
            }
            
        except RedisError as e:
            # Fail open on Redis errors
            logger.error(f"Redis error in rate limiter: {e}")
            return {
                "allowed": True,
                "limit": limit,
                "remaining": limit - 1,
                "retry_after": 0
            }

    async def _rate_limit_response(self, request: Request, limit: int, remaining: int, retry_after: int) -> JSONResponse:
        """Create rate limit response with appropriate headers."""
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": f"Rate limit exceeded: {limit} requests per {self.window} seconds",
                "retry_after": retry_after
            }
        )
        
        # Add rate limit headers (RFC 6585)
        response.headers.update({
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(int(time.time()) + retry_after),
            "Retry-After": str(retry_after)
        })
        
        return response

    def __call__(self, func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            async def call_func():
                if asyncio.iscoroutinefunction(func):
                    return await func(request, *args, **kwargs)
                return await run_in_threadpool(func, request, *args, **kwargs)

            if self.skip:
                return await call_func()
                
            try:
                # Get rate limit key
                identifier = await self._get_identifier(request)
                limit, window = await self._get_limits(request)
                key = f"rate_limit:{self.key_prefix}:{identifier}"
                
                # Check rate limit
                result = await self._check_rate_limit(key, limit, window)
                
                if not result["allowed"]:
                    return await self._rate_limit_response(
                        request,
                        limit=result["limit"],
                        remaining=result["remaining"],
                        retry_after=result["retry_after"]
                    )
                
                # Add rate limit headers to successful responses
                response = await call_func()

                if isinstance(response, Response):
                    response.headers.update({
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": str(result["remaining"]),
                        "X-RateLimit-Reset": str(int(time.time()) + self.window)
                    })
                return response
                
            except Exception as e:
                # Always allow requests through on error
                print(f"Error in rate limiter: {e}")
                return await call_func()
                
        return wrapper

# Global rate limit decorator
def rate_limit(
    key_prefix: str,
    limit: int = 60,
    window: int = 60,
    user_based: bool = False,
    skip: bool = False
):
    """Decorator to apply rate limiting to a route."""
    def decorator(func):
        limiter = RateLimiter(
            key_prefix=key_prefix,
            limit=limit,
            window=window,
            user_based=user_based,
            skip=skip
        )
        return limiter(func)
    return decorator

class RateLimitMiddleware:
    """
    Global rate limiting middleware using Redis.
    Safe for production. Standard ASGI implementation.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Only rate limit HTTP and WebSocket upgrade requests
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Skip health & docs
        path = scope.get("path", "")
        if path.startswith(("/docs", "/redoc", "/openapi", "/health")):
            await self.app(scope, receive, send)
            return

        # Bypassing established WebSockets (Starlette/FastAPI handles the upgrade)
        # We only rate limit the handshake (the initial HTTP-like request)
        # In ASGI, a WebSocket connection starts with scope['type'] == 'websocket'
        
        redis = await get_async_redis()

        # Identifier (IP-based)
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        key = f"rate_limit:{path}:{client_ip}"

        limit = settings.RATE_LIMIT_DEFAULT
        window = settings.RATE_LIMIT_WINDOW

        try:
            current = await redis.incr(key)
            current = int(current)

            if current == 1:
                await redis.expire(key, window)

            if current > limit:
                ttl = await redis.ttl(key)
                retry_after = max(ttl, 1)
                
                if scope["type"] == "http":
                    # Return 429 for HTTP
                    await send({
                        "type": "http.response.start",
                        "status": 429,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"retry-after", str(retry_after).encode()),
                        ],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": f'{{"detail": "Too many requests", "retry_after": {retry_after}}}'.encode(),
                    })
                    return
                else:
                    # Close WebSocket for too many attempts
                    await send({"type": "websocket.close", "code": 1008})
                    return

            # Success: Continue to next middleware/app
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.extend([
                        (b"X-RateLimit-Limit", str(limit).encode()),
                        (b"X-RateLimit-Remaining", str(max(0, limit - current)).encode()),
                        (b"X-RateLimit-Reset", str(int(time.time()) + window).encode()),
                    ])
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_wrapper)

        except Exception as e:
            # Fail-open
            logger.error("Rate limiter failure", extra={"error": str(e)}, exc_info=True)
            await self.app(scope, receive, send)

# Apply rate limiting to FastAPI routes
# def apply_rate_limiting(app, global_limits=None):
#     """Apply rate limiting middleware to the FastAPI application."""
#     app.add_middleware(RateLimitMiddleware, global_limits=global_limits)
#     return app