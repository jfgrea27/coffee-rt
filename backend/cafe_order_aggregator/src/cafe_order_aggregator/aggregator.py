"""Aggregation logic for computing metrics."""

import json
from collections import Counter

from redis.asyncio import Redis
from shared import CoffeeOrder


def compute_hourly_metrics(orders: list[CoffeeOrder]) -> dict:
    """Compute metrics for a given hour's orders.

    Args:
        orders: List of orders for the hour

    Returns:
        Dictionary with top_drinks, revenue, and order_count
    """
    if not orders:
        return {
            "top_drinks": [],
            "revenue": 0.0,
            "order_count": 0,
        }

    drink_counts = Counter(order.drink.value for order in orders)
    top_drinks = [drink for drink, _ in drink_counts.most_common(5)]
    revenue = sum(order.price for order in orders)

    return {
        "top_drinks": top_drinks,
        "revenue": round(revenue, 2),
        "order_count": len(orders),
    }


def compute_top5_drinks(orders: list[CoffeeOrder]) -> list[str]:
    """Compute top 5 drinks from orders.

    Args:
        orders: List of orders to analyze

    Returns:
        List of top 5 drink names by order count
    """
    if not orders:
        return []

    drink_counts = Counter(order.drink.value for order in orders)
    return [drink for drink, _ in drink_counts.most_common(5)]


def serialize_orders(orders: list[CoffeeOrder]) -> list[dict]:
    """Serialize orders to JSON-serializable format.

    Args:
        orders: List of orders

    Returns:
        List of order dictionaries
    """
    return [
        {
            "id": order.id,
            "drink": order.drink.value,
            "store": order.store.value,
            "price": order.price,
            "timestamp": order.timestamp.isoformat(),
        }
        for order in orders
    ]


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
