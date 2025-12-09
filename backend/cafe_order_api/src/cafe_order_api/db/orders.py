"""Database operations for orders."""

from datetime import datetime
from decimal import Decimal

from psycopg import AsyncConnection
from shared import Drink, Store

from cafe_order_api.env import POSTGRES_SCHEMA


async def insert_order(
    db: AsyncConnection,
    drink: Drink,
    store: Store,
    price: float,
    timestamp: datetime,
) -> int:
    """Insert a new order into the database and return the order ID."""
    async with db.cursor() as cur:
        await cur.execute(
            f"""
            INSERT INTO {POSTGRES_SCHEMA}.orders (drink, store, price, timestamp)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (drink.value, store.value, Decimal(str(price)), timestamp),
        )
        result = await cur.fetchone()
        order_id = result[0]
    await db.commit()
    return order_id
