import os
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone
import dotenv
import uvicorn
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.middleware import RequestIDMiddleware, LoggingMiddleware
from app.core.rate_limit import RateLimitMiddleware 
from contextlib import asynccontextmanager

# Now import local modules
from app.core.locger import logger,setup_logging
from app.core.redis import get_async_redis, get_sync_redis, close_redis_connections, check_redis_health
from app.db.base import Base
from app.db.session import engine
import app.models # Ensure all models are registered

# Import routers
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.admin_payments import router as admin_payments_router
from app.routers.restaurants import router as restaurants_router
from app.routers.drivers import router as drivers_router
from app.routers.customer import router as customer_router
from app.routers.users import router as users_router
from app.routers.orders import router as orders_router
from app.routers.ws_orders import router as ws_orders_router
from app.routers.payments import router as payments_router
from app.routers.menus import router as menus_router
from app.routers.notifications import router as notifications_router
from app.routers.addresses import router as addresses_router
from app.routers.billing import router as billing_router
from app.routers.manage import router as manage_router

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables based on environment
ENV = os.getenv("ENV", "development")
env_file = ".env.prod" if ENV == "production" else ".env.dev"
dotenv.load_dotenv(env_file)

# Get CORS origins from environment variable
raw_origins = os.getenv("CORS_ORIGINS", "")
cors_origins = [
    origin.strip()
    for origin in raw_origins.split(",")
    if origin.strip()
]
print(f"CORS Origins: {cors_origins}")

# --- Lifespan for startup/shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup: initializing resources")
    try:
        # Initialize Redis connections
        await get_async_redis()
        get_sync_redis()
        logger.info("Redis initialized successfully")

        # Create tables (for dev/production safety)
        Base.metadata.create_all(bind=engine)
        # create_all only creates missing TABLES; it never adds a column to an
        # existing one. Same change as alembic revision c41f0a7d9e21, repeated
        # here so the app also starts if migrations were not run.
        if engine.dialect.name == "postgresql":
            from sqlalchemy import text
            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS restaurant_id VARCHAR "
                    "REFERENCES restaurants(id) ON DELETE SET NULL"
                ))
                connection.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_drivers_restaurant_id ON drivers (restaurant_id)"
                ))
        logger.info("Database tables verified/created")

        # Route handlers running in worker threads push websocket events through this loop
        import asyncio
        from app.utils.websocket_manager import manager
        manager.bind_loop(asyncio.get_running_loop())

        # Make sure the built-in payment methods (cash, card on delivery, PayFast) exist
        from app.db.session import SessionLocal
        from app.services.payment_service import ensure_default_payment_providers
        with SessionLocal() as db:
            ensure_default_payment_providers(db)
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield  # Application is running

    # Shutdown
    logger.info("Application shutdown: cleaning up resources")
    try:
        await close_redis_connections()
        logger.info("Redis connections closed")
    except Exception as e:
        logger.error(f"Error closing Redis connections: {e}")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="L'vovo Chicken Dust API",
    description="Backend API for L'vovo Chicken Dust food ordering platform",
    version="0.1.0",
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
    lifespan=lifespan,
)
# --- Middleware Configuration ---
# CORS first to handle preflights and handshakes early
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Request-ID"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
)

# Custom middlewares
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# --- API Routes ---
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(restaurants_router, prefix="/api/v1/restaurant", tags=["Restaurants"])
app.include_router(menus_router, prefix="/api/v1/menus", tags=["Menus"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(ws_orders_router, prefix="/api/v1/ws/orders", tags=["WebSocket Orders"])
app.include_router(drivers_router, prefix="/api/v1/drivers", tags=["Drivers"])
app.include_router(payments_router, prefix="/api/v1", tags=["Payments"])
app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(admin_payments_router, prefix="/api/v1", tags=["Admin Payments"])
app.include_router(customer_router, prefix="/api/v1/customer", tags=["Customer"])
app.include_router(addresses_router, prefix="/api/v1", tags=["Addresses"])
app.include_router(billing_router, prefix="/api/v1")
app.include_router(manage_router, prefix="/api/v1")

# setup_logging() 


# --- Health check ---
@app.get("/health", summary="Health Check")
async def health_check() -> Dict[str, Any]:
    try:
        redis_healthy = await check_redis_health()
        return {
            "status": "healthy" if redis_healthy else "degraded",
            "environment": ENV,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dependencies": {"redis": "connected" if redis_healthy else "disconnected"}
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service is unhealthy")

# --- Root endpoint ---
@app.get("/", summary="API Information")
async def root() -> Dict[str, Any]:
    return {"name": app.title, "version": app.version, "environment": ENV, "status": "operational"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.scope.get("request_id", "missing")

    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={"req_id": request_id}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id
        }
    )

# --- Global exception handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.scope.get("request_id", "missing")
    logger.error( f"Unhandled exception: {exc}", extra={"req_id": request_id}, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "request_id": request_id, "error": str(exc) if ENV != "production" else None}
    )

# --- Main Execution ---
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=ENV == "development",
        log_level="info",
        access_log=True,
    )