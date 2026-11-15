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
from app.routers.platform import router as platform_router
from app.routers.reports import router as reports_router
from app.routers.categories import router as categories_router

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
                for column in (
                    "category VARCHAR",
                    "accepting_orders BOOLEAN NOT NULL DEFAULT TRUE",
                    "opens_at VARCHAR(5)",
                    "closes_at VARCHAR(5)",
                    "vat_number VARCHAR(20)",
                    "phone VARCHAR(20)",
                    "menu_sections JSON",
                ):
                    connection.execute(text(f"ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS {column}"))
                for table, column in (
                    ("menu_items", "section VARCHAR(40)"),
                    ("menu_items", "options JSON"),
                    ("order_items", "options JSON"),
                ):
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column}"))
                for column in (
                    "ozow_enabled BOOLEAN NOT NULL DEFAULT FALSE",
                    "ozow_site_code VARCHAR",
                    "ozow_client_id VARCHAR",
                    "ozow_client_secret_enc VARCHAR",
                    "ozow_sandbox BOOLEAN NOT NULL DEFAULT FALSE",
                    "peach_enabled BOOLEAN NOT NULL DEFAULT FALSE",
                    "peach_entity_id VARCHAR",
                    "peach_secret_token_enc VARCHAR",
                    "peach_sandbox BOOLEAN NOT NULL DEFAULT FALSE",
                ):
                    connection.execute(text(f"ALTER TABLE restaurant_payment_settings ADD COLUMN IF NOT EXISTS {column}"))
                connection.execute(text("ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS invoice_number INTEGER"))
                connection.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_subscription_payments_invoice_number "
                    "ON subscription_payments (invoice_number)"
                ))

            # One PayFast charge can be recorded once. Its own transaction: if old data
            # already holds a duplicate, the app still starts and the log says so.
            try:
                with engine.begin() as connection:
                    connection.execute(text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_subscription_payments_pf_charge "
                        "ON subscription_payments (reference) WHERE method = 'payfast' AND status = 'completed'"
                    ))
            except Exception as exc:
                logger.error(f"Could not add the one-charge-once rule for PayFast payments (duplicate rows?): {exc}")
            # Values added to the Python enums after the database types were first
            # created. Without them Postgres rejects the value: accepting an order
            # when no driver is free ("waiting for driver") failed with a 500, and
            # so did the job that cancels stale orders.
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(text("ALTER TYPE order_status_enum ADD VALUE IF NOT EXISTS 'WAITING_FOR_DRIVER'"))
                connection.execute(text("ALTER TYPE role_enum ADD VALUE IF NOT EXISTS 'ADMIN'"))
        logger.info("Database tables verified/created")

        # Route handlers running in worker threads push websocket events through this loop
        import asyncio
        from app.utils.websocket_manager import manager
        manager.bind_loop(asyncio.get_running_loop())

        # Make sure the built-in payment methods (cash, card on delivery, PayFast) exist
        from app.db.session import SessionLocal
        from app.services.payment_service import ensure_default_payment_providers
        from app.services.categories import ensure_defaults as ensure_default_categories
        with SessionLocal() as db:
            ensure_default_payment_providers(db)
            ensure_default_categories(db)
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
    title="Deliver Eats API",
    description="Backend API for Deliver Eats, a food delivery marketplace for local restaurants",
    version="0.1.0",
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
    lifespan=lifespan,
)
# --- Middleware Configuration ---
# The LAST middleware added runs FIRST. CORS is added last so it wraps
# everything, including the rate limiter's 429 reply: without CORS headers the
# browser hides that reply and the app could only show "network error".
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Request-ID"],
    expose_headers=["Content-Disposition", "X-Request-ID", "Retry-After"],
)

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
app.include_router(platform_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")

# Uploaded restaurant logos
from fastapi.staticfiles import StaticFiles  # noqa: E402
from app.services.uploads import PUBLIC_PREFIX, upload_root  # noqa: E402
app.mount(PUBLIC_PREFIX, StaticFiles(directory=upload_root()), name="uploads")

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