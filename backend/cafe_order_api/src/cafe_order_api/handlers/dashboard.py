"""Dashboard handler for retrieving metrics from Redis."""

import json
from datetime import datetime

from redis.asyncio import Redis

from cafe_order_api.domain import DashboardResponse, HourlyMetrics, RecentOrder


async def get_dashboard(redis: Redis) -> DashboardResponse:
    """Fetch dashboard metrics from Redis cache.

    Args:
        redis: Redis connection

    Returns:
        DashboardResponse with current hour metrics, top 5 drinks, and recent orders
    """
    current_hour = datetime.now().hour

    # Fetch all metrics from Redis
    hourly_data = await redis.get(f"metrics:hourly:{current_hour}")
    top5_data = await redis.get("metrics:top5")
    recent_data = await redis.get("orders:recent")

    # Parse hourly metrics
    current_hour_metrics = None
    if hourly_data:
        hourly = json.loads(hourly_data)
        current_hour_metrics = HourlyMetrics(
            hour=current_hour,
            top_drinks=hourly.get("top_drinks", []),
            revenue=hourly.get("revenue", 0.0),
            order_count=hourly.get("order_count", 0),
        )

    # Parse top 5 drinks
    top5_drinks = []
    if top5_data:
        top5_drinks = json.loads(top5_data)

    # Parse recent orders
    recent_orders = []
    if recent_data:
        orders = json.loads(recent_data)
        recent_orders = [RecentOrder(**order) for order in orders]

    return DashboardResponse(
        current_hour=current_hour_metrics,
        top5_drinks=top5_drinks,
        recent_orders=recent_orders,
    )
