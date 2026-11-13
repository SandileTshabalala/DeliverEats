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

# Paths with their own, much stricter limit (password guessing, sign-up spam)
AUTH_PATHS = (
    "/api/v1/auth/login", "/api/v1/auth/register",
    "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password",
)
# Called by PayFast's servers, never by browsers: must not be throttled
WEBHOOK_PATHS = ("/api/v1/payments/payfast/notify", "/api/v1/billing/payfast/notify")
UNLIMITED_PREFIXES = ("/docs", "/redoc", "/openapi", "/health")


def _client_ip(scope) -> str:
    """
    Real caller address. In production the app sits behind nginx, so every
    connection comes from the proxy: without this, all users would share ONE
    limit and lock each other out. nginx sets X-Real-IP itself (it cannot be
    spoofed through the proxy), so it is only trusted in production.
    """
    if settings.is_production:
        headers = dict(scope.get("headers") or [])
        real_ip = headers.get(b"x-real-ip", b"").decode().strip()
        if real_ip:
            return real_ip
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    """
    Global rate limiting using Redis (fixed window per client address).

    - sign-in / sign-up: RATE_LIMIT_AUTH per window, counted together
    - everything else:   RATE_LIMIT_DEFAULT per window, across the whole API
    - if Redis is down the limiter fails open: requests are served, not blocked
    """
    def __init__(self, app):
        self.app = app

    async def _check(self, scope, path):
        """Returns (limit, used, retry_after) or None when the limiter is unavailable."""
        if path in AUTH_PATHS:
            bucket, limit = "auth", settings.RATE_LIMIT_AUTH
        else:
            bucket, limit = "api", settings.RATE_LIMIT_DEFAULT
        window = settings.RATE_LIMIT_WINDOW
        key = f"rate_limit:{bucket}:{_client_ip(scope)}"
        try:
            redis = await get_async_redis()
            # SET NX EX + INCR: the key always has an expiry, so a client can
            # never be locked out forever if the process dies between two calls
            await redis.set(key, 0, ex=window, nx=True)
            used = int(await redis.incr(key))
            retry_after = 0
            if used > limit:
                retry_after = max(int(await redis.ttl(key)), 1)
            return limit, used, retry_after
        except Exception as e:
            logger.error("Rate limiter unavailable, allowing request", extra={"error": str(e)})
            return None

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith(UNLIMITED_PREFIXES) or path in WEBHOOK_PATHS or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        result = await self._check(scope, path)
        if result is None:
            await self.app(scope, receive, send)
            return
        limit, used, retry_after = result

        if retry_after:
            if scope["type"] == "http":
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
                    "body": f'{{"detail": "Too many requests. Please wait a moment and try again.", "retry_after": {retry_after}}}'.encode(),
                })
            else:
                await send({"type": "websocket.close", "code": 1008})
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"X-RateLimit-Limit", str(limit).encode()),
                    (b"X-RateLimit-Remaining", str(max(0, limit - used)).encode()),
                ])
                message["headers"] = headers
            await send(message)

        # The app is called exactly ONCE and outside any try/except. The old
        # code wrapped this call in "except Exception: await self.app(...)", so
        # any error inside a request ran the whole request a second time (with
        # its body already consumed, which hung the connection forever).
        await self.app(scope, receive, send_wrapper)


# Apply rate limiting to FastAPI routes
# def apply_rate_limiting(app, global_limits=None):
#     """Apply rate limiting middleware to the FastAPI application."""
#     app.add_middleware(RateLimitMiddleware, global_limits=global_limits)
#     return app