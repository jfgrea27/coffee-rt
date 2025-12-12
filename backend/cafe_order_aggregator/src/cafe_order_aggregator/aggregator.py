"""Aggregation job for computing and caching metrics."""

import asyncio
import logging
from datetime import UTC, datetime

from psycopg import AsyncConnection, OperationalError
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from cafe_order_aggregator.db.queries import (
    get_orders_for_hour,
    get_orders_last_30_days,
    get_recent_orders,
)
from cafe_order_aggregator.env import APP_TITLE, DATABASE_URL, REDIS_URL
from cafe_order_aggregator.redis_client import (
    update_hourly_metrics,
    update_recent_orders,
    update_top5_drinks,
)
from cafe_order_aggregator.utils import (
    compute_hourly_metrics,
    compute_top5_drinks,
)

logger = logging.getLogger(APP_TITLE)

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1


async def connect_with_retry(
    connect_fn,
    service_name: str,
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF_SECONDS,
):
    """Connect to a service with exponential backoff retry.

    Args:
        connect_fn: Async function that returns a connection
        service_name: Name of the service for logging
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds

    Returns:
        Connection object

    Raises:
        Exception: If all retries are exhausted
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await connect_fn()
        except (OperationalError, RedisConnectionError, OSError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                backoff = initial_backoff * (2**attempt)
                logger.warning(
                    f"Failed to connect to {service_name} "
                    f"(attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {backoff}s..."
                )
                await asyncio.sleep(backoff)
            else:
                logger.error(
                    f"Failed to connect to {service_name} after {max_retries} attempts: {e}"
                )
    raise last_exception


async def run_aggregation(
    db: AsyncConnection | None = None,
    redis: Redis | None = None,
) -> dict:
    """Run all aggregation tasks and update Redis cache.

    Args:
        db: Optional database connection (creates one if not provided)
        redis: Optional Redis connection (creates one if not provided)

    Returns:
        Dictionary with aggregation results
    """
    logger.info("Starting aggregation job")

    # Track whether we created the connections (for cleanup)
    created_db = db is None
    created_redis = redis is None

    # Connect to database with retry if not provided
    if db is None:
        logger.info("Connecting to database...")
        db = await connect_with_retry(
            lambda: AsyncConnection.connect(DATABASE_URL),
            "database",
        )

    # Connect to Redis with retry if not provided
    if redis is None:
        logger.info("Connecting to Redis...")

        async def connect_redis():
            client = Redis.from_url(REDIS_URL)
            await client.ping()  # Verify connection
            return client

        redis = await connect_with_retry(connect_redis, "Redis")

    try:
        # 1. Update hourly metrics for current hour (UTC)
        current_hour = datetime.now(UTC).hour
        logger.info(f"Fetching orders for hour {current_hour}")
        hourly_orders = await get_orders_for_hour(db, current_hour)
        hourly_metrics = compute_hourly_metrics(hourly_orders)
        await update_hourly_metrics(redis, current_hour, hourly_metrics)
        logger.info(
            f"Updated metrics:hourly:{current_hour} - "
            f"{hourly_metrics['order_count']} orders, ${hourly_metrics['revenue']} revenue"
        )

        # 2. Update top 5 drinks from last 30 days
        logger.info("Fetching orders from last 30 days")
        monthly_orders = await get_orders_last_30_days(db)
        top5 = compute_top5_drinks(monthly_orders)
        await update_top5_drinks(redis, top5)
        logger.info(f"Updated metrics:top5 - {top5}")

        # 3. Update recent orders (last hour)
        logger.info("Fetching recent orders")
        recent_orders = await get_recent_orders(db)
        await update_recent_orders(redis, recent_orders)
        logger.info(f"Updated orders:recent - {len(recent_orders)} orders")

        logger.info("Aggregation job completed successfully")

        return {
            "hourly_metrics": hourly_metrics,
            "top5_drinks": top5,
            "recent_orders_count": len(recent_orders),
        }

    finally:
        # Only close connections we created
        if created_redis and redis:
            await redis.close()
            logger.info("Redis connection closed")
        if created_db and db:
            await db.close()
            logger.info("Database connection closed")
