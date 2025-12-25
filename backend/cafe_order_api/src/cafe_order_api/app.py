import logging
from contextlib import asynccontextmanager

import uvicorn
from aiokafka import AIOKafkaProducer
from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis
from shared import get_uvicorn_config, setup_logging

from cafe_order_api.domain import (
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
    DB_POOL_MAX_SIZE,
    DB_POOL_MIN_SIZE,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_ENABLED,
    LOG_FILE,
    REDIS_URL,
    REDIS_URL_SANITIZED,
)
from cafe_order_api.handlers.dashboard import get_dashboard as handle_get_dashboard
from cafe_order_api.handlers.websocket import dashboard_websocket_handler
from cafe_order_api.metrics import APP_INFO
from cafe_order_api.middelware import MetricsMiddleware, ServiceHealthMiddleware
from cafe_order_api.routers import v1_router, v2_router, v3_router
from cafe_order_api.utils import connect_with_retry

app = FastAPI()


setup_logging(LOG_FILE)


logger = logging.getLogger(APP_TITLE)


async def get_redis_connection(request: Request) -> Redis:
    """Get Redis connection from app state."""
    return request.app.state.redis_connection


async def get_db_connection(request: Request):
    """Get database connection from pool."""
    async with request.app.state.db_pool.connection() as conn:
        yield conn


async def _init_db_pool(app: FastAPI):
    """Initialize database connection pool and update app state."""

    async def create_pool():
        pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=DB_POOL_MIN_SIZE,
            max_size=DB_POOL_MAX_SIZE,
            open=False,
        )
        await pool.open()
        await pool.check()  # Verify pool is working
        return pool

    result = await connect_with_retry(
        create_pool,
        "database pool",
        max_retries=CONNECTION_MAX_RETRIES,
        initial_backoff=CONNECTION_INITIAL_BACKOFF,
    )
    if isinstance(result, tuple):
        _, error = result
        app.state.db_ready = False
        app.state.db_error = str(error)
        logger.warning(f"Failed to initialize database pool: {error}")
        return None
    else:
        logger.info(
            f"Database connection pool initialized (min={DB_POOL_MIN_SIZE}, max={DB_POOL_MAX_SIZE})"
        )
        app.state.db_ready = True
        app.state.db_error = None
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
        app.state.redis_ready = False
        app.state.redis_error = str(error)
        logger.warning(f"Failed to initialize Redis connection: {error}")
        return None
    else:
        logger.info("Redis connection initialized")
        app.state.redis_ready = True
        app.state.redis_error = None
        return result


async def _init_kafka_producer(app: FastAPI):
    """Initialize Kafka producer and update app state."""
    if not KAFKA_ENABLED:
        logger.info("Kafka is disabled, skipping producer initialization")
        app.state.kafka_producer = None
        app.state.kafka_ready = False
        app.state.kafka_error = "Kafka disabled"
        return None

    async def create_producer():
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            enable_idempotence=True,  # Exactly-once semantics
            # Batching for throughput - collect messages for up to 5ms
            linger_ms=5,
            # Batch size in bytes (16KB default, increase for high throughput)
            max_batch_size=32768,
            # Compression for better network efficiency
            compression_type="lz4",
        )
        await producer.start()
        return producer

    result = await connect_with_retry(
        create_producer,
        "Kafka producer",
        max_retries=CONNECTION_MAX_RETRIES,
        initial_backoff=CONNECTION_INITIAL_BACKOFF,
    )
    if isinstance(result, tuple):
        _, error = result
        app.state.kafka_ready = False
        app.state.kafka_error = str(error)
        app.state.kafka_producer = None
        logger.warning(f"Failed to initialize Kafka producer: {error}")
        return None
    else:
        logger.info(f"Kafka producer initialized (servers={KAFKA_BOOTSTRAP_SERVERS})")
        app.state.kafka_ready = True
        app.state.kafka_error = None
        return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application lifespan."""
    logger.info("Application startup complete")
    app.state.db_ready = False
    app.state.db_error = None
    app.state.redis_ready = False
    app.state.redis_error = None
    app.state.kafka_ready = False
    app.state.kafka_error = None
    app.state.kafka_producer = None

    db_pool = await _init_db_pool(app)
    app.state.db_pool = db_pool
    redis_connection = await _init_redis_connection(app)
    app.state.redis_connection = redis_connection
    kafka_producer = await _init_kafka_producer(app)
    app.state.kafka_producer = kafka_producer

    yield

    if kafka_producer:
        try:
            await kafka_producer.stop()
            logger.info("Kafka producer stopped")
        except Exception as e:
            logger.warning(f"Error stopping Kafka producer: {e}")

    if redis_connection:
        try:
            await redis_connection.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")

    if db_pool:
        try:
            await db_pool.close()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.warning(f"Error closing database pool: {e}")

    logger.info("Application shutdown complete")


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# Set application info for Prometheus
APP_INFO.info({"version": APP_VERSION, "title": APP_TITLE})

# Add middleware (order matters)
app.add_middleware(MetricsMiddleware)
app.add_middleware(ServiceHealthMiddleware)

# Mount versioned API routers
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")
app.include_router(v3_router, prefix="/api/v3")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


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

    If connections are down, attempts to reconnect and update app state.
    """
    # Attempt to reconnect to database if not ready
    if not app.state.db_ready or app.state.db_error:
        logger.info("Database pool not ready, attempting to reconnect...")
        db_pool = await _init_db_pool(app)
        if db_pool:
            # Close old pool if it exists
            if app.state.db_pool:
                try:
                    await app.state.db_pool.close()
                except Exception:
                    pass
            app.state.db_pool = db_pool

    # Attempt to reconnect to Redis if not ready
    if not app.state.redis_ready or app.state.redis_error:
        logger.info("Redis connection not ready, attempting to reconnect...")
        redis_connection = await _init_redis_connection(app)
        if redis_connection:
            # Close old connection if it exists
            if app.state.redis_connection:
                try:
                    await app.state.redis_connection.close()
                except Exception:
                    pass
            app.state.redis_connection = redis_connection

    # Attempt to reconnect to Kafka if enabled and not ready
    if KAFKA_ENABLED and (not app.state.kafka_ready or app.state.kafka_error):
        logger.info("Kafka producer not ready, attempting to reconnect...")
        kafka_producer = await _init_kafka_producer(app)
        if kafka_producer:
            # Stop old producer if it exists
            if app.state.kafka_producer:
                try:
                    await app.state.kafka_producer.stop()
                except Exception:
                    pass
            app.state.kafka_producer = kafka_producer

    connections = {
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
    }

    # Include Kafka status if enabled
    if KAFKA_ENABLED:
        connections["kafka"] = {
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
            "ready": app.state.kafka_ready,
            "error": app.state.kafka_error,
        }

    # Determine overall status based on all connections
    db_ok = app.state.db_ready and not app.state.db_error
    redis_ok = app.state.redis_ready and not app.state.redis_error
    kafka_ok = not KAFKA_ENABLED or (app.state.kafka_ready and not app.state.kafka_error)
    all_ok = db_ok and redis_ok and kafka_ok

    res = HealthResponse(
        status="ok" if all_ok else "error",
        service=APP_TITLE,
        version=APP_VERSION,
        connections=connections,
    )
    logger.info(f"Readiness check: {res.model_dump_json()}")

    if not db_ok:
        raise HTTPException(status_code=503, detail="Database connection not available")
    if not redis_ok:
        raise HTTPException(status_code=503, detail="Redis connection not available")
    if not kafka_ok:
        raise HTTPException(status_code=503, detail="Kafka producer not available")

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
