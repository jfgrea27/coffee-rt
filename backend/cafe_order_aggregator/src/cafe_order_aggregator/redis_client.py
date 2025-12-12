"""Redis client functions for updating cached metrics."""

import json

from redis.asyncio import Redis
from shared import CoffeeOrder

from cafe_order_aggregator.utils import serialize_orders


async def update_hourly_metrics(redis: Redis, hour: int, metrics: dict) -> None:
    """Update Redis cache with hourly metrics.

    Args:
        redis: Redis connection
        hour: Hour of the day (0-23)
        metrics: Computed metrics dictionary
    """
    key = f"metrics:hourly:{hour}"
    await redis.set(key, json.dumps(metrics))
    # Expire after 25 hours to ensure we keep data for the current day cycle
    await redis.expire(key, 25 * 3600)


async def update_top5_drinks(redis: Redis, top_drinks: list[str]) -> None:
    """Update Redis cache with top 5 drinks.

    Args:
        redis: Redis connection
        top_drinks: List of top 5 drink names
    """
    key = "metrics:top5"
    await redis.set(key, json.dumps(top_drinks))
    # No expiry - this is a rolling 30-day metric


async def update_recent_orders(redis: Redis, orders: list[CoffeeOrder]) -> None:
    """Update Redis cache with recent orders.

    Args:
        redis: Redis connection
        orders: List of recent orders
    """
    key = "orders:recent"
    serialized = serialize_orders(orders)
    await redis.set(key, json.dumps(serialized))
    # Expire after 2 hours to ensure staleness is detected
    await redis.expire(key, 2 * 3600)
