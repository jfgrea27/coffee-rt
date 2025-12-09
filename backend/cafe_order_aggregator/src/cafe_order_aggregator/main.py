"""Main entry point for cafe order aggregator."""

import asyncio
import logging
from datetime import datetime

from psycopg import AsyncConnection
from redis.asyncio import Redis

from cafe_order_aggregator.aggregator import (
    compute_hourly_metrics,
    compute_top5_drinks,
    update_hourly_metrics,
    update_recent_orders,
    update_top5_drinks,
)
from cafe_order_aggregator.db.queries import (
    get_orders_for_hour,
    get_orders_last_30_days,
    get_recent_orders,
)
from cafe_order_aggregator.env import DATABASE_URL, REDIS_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_aggregation() -> None:
    """Run all aggregation tasks and update Redis cache."""
    logger.info("Starting aggregation job")

    # Connect to database
    logger.info("Connecting to database...")
    db = await AsyncConnection.connect(DATABASE_URL)

    # Connect to Redis
    logger.info("Connecting to Redis...")
    redis = Redis.from_url(REDIS_URL)

    try:
        # 1. Update hourly metrics for current hour
        current_hour = datetime.now().hour
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

    finally:
        await redis.close()
        await db.close()
        logger.info("Connections closed")


def main() -> None:
    """CLI entry point."""
    asyncio.run(run_aggregation())


if __name__ == "__main__":
    main()
