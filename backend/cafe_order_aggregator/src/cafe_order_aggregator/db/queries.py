"""Database queries for order aggregation."""

from datetime import UTC, datetime, timedelta

from psycopg import AsyncConnection
from shared import CoffeeOrder, Drink, Store

from cafe_order_aggregator.env import POSTGRES_SCHEMA


async def get_orders_for_hour(db: AsyncConnection, hour: int) -> list[CoffeeOrder]:
    """Get all orders for a specific hour today (UTC).

    Args:
        db: Database connection
        hour: Hour of the day (0-23) in UTC

    Returns:
        List of orders for the specified hour
    """
    today = datetime.now(UTC).date()
    start_time = datetime.combine(today, datetime.min.time().replace(hour=hour), tzinfo=UTC)
    end_time = start_time + timedelta(hours=1)

    async with db.cursor() as cur:
        await cur.execute(
            f"""
            SELECT id, drink, store, price, timestamp
            FROM {POSTGRES_SCHEMA}.orders
            WHERE timestamp >= %s AND timestamp < %s
            ORDER BY timestamp DESC
            """,
            (start_time, end_time),
        )
        rows = await cur.fetchall()

    return [
        CoffeeOrder(
            id=row[0],
            drink=Drink(row[1]),
            store=Store(row[2]),
            price=float(row[3]),
            timestamp=row[4],
        )
        for row in rows
    ]


async def get_orders_last_30_days(db: AsyncConnection) -> list[CoffeeOrder]:
    """Get all orders from the last 30 days.

    Args:
        db: Database connection

    Returns:
        List of orders from the last 30 days
    """
    cutoff = datetime.now(UTC) - timedelta(days=30)

    async with db.cursor() as cur:
        await cur.execute(
            f"""
            SELECT id, drink, store, price, timestamp
            FROM {POSTGRES_SCHEMA}.orders
            WHERE timestamp >= %s
            ORDER BY timestamp DESC
            """,
            (cutoff,),
        )
        rows = await cur.fetchall()

    return [
        CoffeeOrder(
            id=row[0],
            drink=Drink(row[1]),
            store=Store(row[2]),
            price=float(row[3]),
            timestamp=row[4],
        )
        for row in rows
    ]


async def get_recent_orders(db: AsyncConnection, limit: int = 50) -> list[CoffeeOrder]:
    """Get most recent orders from the last hour.

    Args:
        db: Database connection
        limit: Maximum number of orders to return (default 50)

    Returns:
        List of most recent orders from the last hour
    """
    cutoff = datetime.now(UTC) - timedelta(hours=1)

    async with db.cursor() as cur:
        await cur.execute(
            f"""
            SELECT id, drink, store, price, timestamp
            FROM {POSTGRES_SCHEMA}.orders
            WHERE timestamp >= %s
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (cutoff, limit),
        )
        rows = await cur.fetchall()

    return [
        CoffeeOrder(
            id=row[0],
            drink=Drink(row[1]),
            store=Store(row[2]),
            price=float(row[3]),
            timestamp=row[4],
        )
        for row in rows
    ]
