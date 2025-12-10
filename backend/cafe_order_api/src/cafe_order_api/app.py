import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from psycopg import AsyncConnection
from redis.asyncio import Redis
from shared import get_uvicorn_config, setup_logging

from cafe_order_api.domain import (
    CoffeeOrderRequest,
    CoffeeOrderResponse,
    DashboardResponse,
    HealthResponse,
)
from cafe_order_api.env import (
    APP_HOST,
    APP_PORT,
    APP_TITLE,
    APP_VERSION,
    CONNECTION_INITIAL_BACKOFF,
    CONNECTION_MAX_RETRIES,
    DATABASE_URL,
    DATABASE_URL_SANITIZED,
    LOG_FILE,
    REDIS_URL,
    REDIS_URL_SANITIZED,
)
from cafe_order_api.handlers.dashboard import get_dashboard as handle_get_dashboard
from cafe_order_api.handlers.orders import create_order as handle_create_order
from cafe_order_api.handlers.websocket import dashboard_websocket_handler
from cafe_order_api.middelware import ServiceHealthMiddleware
from cafe_order_api.utils import connect_with_retry

app = FastAPI()


setup_logging(LOG_FILE)


logger = logging.getLogger(__name__)


async def get_redis_connection(request: Request) -> Redis:
    """Get Redis connection from app state."""
    return request.app.state.redis_connection


async def get_db_connection(request: Request) -> AsyncConnection:
    """Get database connection from app state."""
    return request.app.state.db_connection


async def _init_db_connection(app: FastAPI):
    """Initialize database connection and update app state."""
    result = await connect_with_retry(
        lambda: AsyncConnection.connect(DATABASE_URL),
        "database",
        max_retries=CONNECTION_MAX_RETRIES,
        initial_backoff=CONNECTION_INITIAL_BACKOFF,
    )
    if isinstance(result, tuple):
        _, error = result
        app.state.db_error = str(error)
        logger.warning(f"Failed to initialize database connection: {error}")
        return None
    else:
        logger.info("Database connection initialized")
        app.state.db_ready = True
        return result


async def _init_redis_connection(app: FastAPI):
    """Initialize Redis connection and update app state."""

    async def connect_redis():
        client = Redis.from_url(REDIS_URL)
        await client.ping()  # Verify connection
        return client

    result = await connect_with_retry(
        connect_redis,
        "Redis",
        max_retries=CONNECTION_MAX_RETRIES,
        initial_backoff=CONNECTION_INITIAL_BACKOFF,
    )
    if isinstance(result, tuple):
        _, error = result
        app.state.redis_error = str(error)
        logger.warning(f"Failed to initialize Redis connection: {error}")
        return None
    else:
        logger.info("Redis connection initialized")
        app.state.redis_ready = True
        return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application lifespan."""
    logger.info("Application startup complete")
    app.state.db_ready = False
    app.state.db_error = None
    app.state.redis_ready = False
    app.state.redis_error = None

    db_connection = await _init_db_connection(app)
    app.state.db_connection = db_connection
    redis_connection = await _init_redis_connection(app)
    app.state.redis_connection = redis_connection

    yield

    if redis_connection:
        try:
            await redis_connection.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")

    if db_connection:
        try:
            await db_connection.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")

    logger.info("Application shutdown complete")


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# Add middleware to check service availability
app.add_middleware(ServiceHealthMiddleware)


@app.get("/livez")
async def liveness_check() -> dict:
    """
    Liveness probe endpoint.

    Returns 200 if the application process is running.
    Does not check external dependencies - only verifies the app is alive.
    """
    logger.info("Liveness check: OK")
    return {"status": "ok"}


@app.get("/readyz")
async def readiness_check() -> HealthResponse:
    """
    Readiness probe endpoint.

    Returns detailed status of all connections and services.
    Returns 503 if the service is not ready to accept traffic.
    """

    res = HealthResponse(
        status="ok",
        service=APP_TITLE,
        version=APP_VERSION,
        connections={
            "database": {
                "db_url": DATABASE_URL_SANITIZED,
                "ready": app.state.db_ready,
                "error": app.state.db_error,
            },
            "redis": {
                "redis_url": REDIS_URL_SANITIZED,
                "ready": app.state.redis_ready,
                "error": app.state.redis_error,
            },
        },
    )
    logger.info(f"Readiness check: {res.model_dump_json()}")

    if not app.state.db_ready or app.state.db_error:
        raise HTTPException(status_code=503, detail="Database connection not available")
    if not app.state.redis_ready or app.state.redis_error:
        raise HTTPException(status_code=503, detail="Redis connection not available")

    return res


@app.post("/api/order")
async def create_order(
    order: CoffeeOrderRequest, db: AsyncConnection = Depends(get_db_connection)
) -> CoffeeOrderResponse:
    """Create a new coffee order."""
    logger.info(f"Creating order: {order}")
    res = await handle_create_order(db=db, order=order)
    logger.info(f"Order created: {res}")
    return res


@app.get("/api/dashboard")
async def get_dashboard(redis: Redis = Depends(get_redis_connection)) -> DashboardResponse:
    """Get dashboard metrics from Redis cache."""
    logger.info(f"Getting dashboard: {redis}")
    res = await handle_get_dashboard(redis=redis)
    logger.info(f"Dashboard: {res}")
    return res


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    redis = app.state.redis_connection
    await dashboard_websocket_handler(websocket, redis)


def main():
    """Run the cafe order API service."""
    uvicorn.run(
        app,
        host=APP_HOST,
        port=int(APP_PORT),
        log_config=get_uvicorn_config(),
    )


if __name__ == "__main__":
    main()
