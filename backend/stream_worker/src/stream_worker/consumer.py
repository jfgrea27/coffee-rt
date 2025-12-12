"""Redis Streams consumer that writes orders to PostgreSQL with real-time metrics."""

import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from psycopg import AsyncConnection
from redis.asyncio import Redis
from redis.exceptions import ResponseError
from shared import CoffeeOrder, Drink, Store

from stream_worker.env import APP_TITLE, POSTGRES_SCHEMA

logger = logging.getLogger(APP_TITLE)


@dataclass
class PendingOrder:
    """Order pending insertion with its stream message ID."""

    message_id: str  # UUID from API for idempotency
    order: CoffeeOrder
    stream_message_id: bytes  # Redis stream message ID for ACK


def parse_order_from_stream(fields: dict[bytes | str, bytes | str]) -> tuple[str, CoffeeOrder]:
    """
    Parse order data from Redis stream message fields.

    Args:
        fields: Raw field dict from Redis stream

    Returns:
        Tuple of (message_id, CoffeeOrder)
    """
    # Decode bytes to strings if needed
    data = {
        k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
        for k, v in fields.items()
    }

    return data["message_id"], CoffeeOrder(
        drink=Drink(data["drink"]),
        store=Store(data["store"]),
        price=float(data["price"]),
        timestamp=datetime.fromisoformat(data["timestamp"]),
    )


async def process_orders_batch(
    db: AsyncConnection, redis_client: Redis, pending_orders: list[PendingOrder]
) -> list[CoffeeOrder]:
    """
    Process a batch of orders, inserting into PostgreSQL in a single transaction.

    Args:
        db: Database connection
        redis_client: Redis async client for metrics updates
        pending_orders: List of pending orders to insert

    Returns:
        List of successfully inserted orders (with IDs populated)
    """
    if not pending_orders:
        return []

    inserted_orders: list[CoffeeOrder] = []

    try:
        # Prepare batch data
        values = [
            (
                po.message_id,
                po.order.drink.value,
                po.order.store.value,
                Decimal(str(po.order.price)),
                po.order.timestamp,
            )
            for po in pending_orders
        ]

        async with db.cursor() as cur:
            placeholders = ",".join(["(%s, %s, %s, %s, %s)"] * len(values))
            flat_values = [v for row in values for v in row]

            await cur.execute(
                f"""
                INSERT INTO {POSTGRES_SCHEMA}.orders (message_id, drink, store, price, timestamp)
                VALUES {placeholders}
                ON CONFLICT (message_id) DO NOTHING
                RETURNING id, message_id
                """,
                flat_values,
            )
            results = await cur.fetchall()

            # Map inserted message_ids to their DB IDs
            message_id_to_db_id: dict[str, int] = {row[1]: row[0] for row in results}

            # Build inserted orders with their DB IDs
            for po in pending_orders:
                if po.message_id in message_id_to_db_id:
                    order_with_id = CoffeeOrder(
                        id=message_id_to_db_id[po.message_id],
                        drink=po.order.drink,
                        store=po.order.store,
                        price=po.order.price,
                        timestamp=po.order.timestamp,
                    )
                    inserted_orders.append(order_with_id)

        await db.commit()

        # Update metrics for all successfully inserted orders
        if inserted_orders:
            await update_metrics_batch(redis_client, inserted_orders)
            skipped = len(pending_orders) - len(inserted_orders)
            logger.info(
                f"Batch inserted {len(inserted_orders)} orders (skipped {skipped} duplicates)"
            )

        return inserted_orders

    except Exception as e:
        logger.error(f"Failed to process batch: {e}")
        try:
            await db.rollback()
        except Exception:
            pass
        return []


async def update_metrics_batch(redis_client: Redis, orders: list[CoffeeOrder]) -> None:
    """
    Update real-time metrics in Redis for a batch of orders.

    Updates the same keys as v1 aggregator:
    - metrics:hourly:{hour} - JSON with top_drinks, revenue, order_count
    - metrics:top5 - JSON array of top 5 drinks
    - orders:recent - JSON array of recent orders

    Args:
        redis_client: Redis async client
        orders: List of CoffeeOrder objects with IDs
    """
    if not orders:
        return

    current_hour = datetime.now(UTC).hour

    # Compute metrics for this batch
    drink_counts = Counter(order.drink.value for order in orders)
    top_drinks = [drink for drink, _ in drink_counts.most_common(5)]
    revenue = sum(order.price for order in orders)
    order_count = len(orders)

    # Get existing hourly metrics to merge
    hourly_key = f"metrics:hourly:{current_hour}"
    existing_hourly = await redis_client.get(hourly_key)

    if existing_hourly:
        existing = json.loads(existing_hourly)
        # Merge drink counts for top calculation
        existing_drinks = Counter(existing.get("drink_counts", {}))
        combined_drinks = existing_drinks + drink_counts
        top_drinks = [drink for drink, _ in combined_drinks.most_common(5)]
        # Accumulate totals
        revenue += existing.get("revenue", 0.0)
        order_count += existing.get("order_count", 0)
        # Store drink counts for future merges
        drink_counts_dict = dict(combined_drinks)
    else:
        drink_counts_dict = dict(drink_counts)

    hourly_metrics = {
        "top_drinks": top_drinks,
        "revenue": round(revenue, 2),
        "order_count": order_count,
        "drink_counts": drink_counts_dict,
    }

    # Prepare recent orders (last 10) - must include id for dashboard
    recent_orders = [
        {
            "id": order.id,
            "drink": order.drink.value,
            "store": order.store.value,
            "price": order.price,
            "timestamp": order.timestamp.isoformat(),
        }
        for order in orders[-10:]
    ]

    # Update Redis
    pipe = redis_client.pipeline()
    pipe.set(hourly_key, json.dumps(hourly_metrics))
    pipe.expire(hourly_key, 25 * 3600)
    pipe.set("metrics:top5", json.dumps(top_drinks))
    pipe.set("orders:recent", json.dumps(recent_orders))
    pipe.expire("orders:recent", 2 * 3600)
    await pipe.execute()

    logger.debug(f"Updated metrics for {len(orders)} orders (hour={current_hour})")


async def ensure_consumer_group(redis_client: Redis, stream_name: str, group_name: str) -> None:
    """
    Create consumer group if it doesn't exist.

    Args:
        redis_client: Redis async client
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
    """
    try:
        await redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
        logger.info(f"Created consumer group '{group_name}' for stream '{stream_name}'")
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group '{group_name}' already exists")
        else:
            raise


async def consume_stream(
    redis_client: Redis,
    db: AsyncConnection,
    stream_name: str,
    group_name: str,
    consumer_name: str,
    batch_size: int = 100,
    batch_timeout_ms: int = 2000,
) -> None:
    """
    Consume messages from Redis Stream using consumer groups with batching.

    Collects orders until batch_size is reached OR batch_timeout_ms elapses,
    then flushes to database in a single transaction.

    Args:
        redis_client: Redis async client
        db: Database connection
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        consumer_name: Unique name for this consumer instance
        batch_size: Number of orders to collect before flushing (default 100)
        batch_timeout_ms: Max time to wait before flushing partial batch (default 2000ms)
    """
    logger.info(
        f"Starting stream consumer: stream={stream_name}, "
        f"group={group_name}, consumer={consumer_name}, "
        f"batch_size={batch_size}, batch_timeout_ms={batch_timeout_ms}"
    )

    # Batch accumulators
    pending_orders: list[PendingOrder] = []

    async def flush_batch() -> None:
        """Flush pending orders to database and ACK messages."""
        nonlocal pending_orders

        if not pending_orders:
            return

        batch = pending_orders
        pending_orders = []

        try:
            await process_orders_batch(db, redis_client, batch)

            # ACK all messages
            stream_message_ids = [po.stream_message_id for po in batch]
            if stream_message_ids:
                await redis_client.xack(stream_name, group_name, *stream_message_ids)
                logger.debug(f"Acknowledged {len(stream_message_ids)} messages")
        except Exception as e:
            logger.error(f"Failed to flush batch: {e}")
            raise

    while True:
        try:
            # Use short block time to allow periodic flushing
            messages = await redis_client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_name: ">"},
                count=batch_size - len(pending_orders),
                block=batch_timeout_ms,
            )

            if messages:
                for stream, stream_messages in messages:
                    for stream_message_id, fields in stream_messages:
                        try:
                            message_id, order = parse_order_from_stream(fields)
                            pending_orders.append(
                                PendingOrder(
                                    message_id=message_id,
                                    order=order,
                                    stream_message_id=stream_message_id,
                                )
                            )
                        except Exception as e:
                            logger.error(f"Error parsing message {stream_message_id}: {e}")

            # Flush if batch is full OR timeout elapsed with pending orders
            if len(pending_orders) >= batch_size:
                await flush_batch()
            elif pending_orders and not messages:
                # Timeout elapsed with partial batch - flush it
                logger.debug(f"Flushing partial batch of {len(pending_orders)} orders (timeout)")
                await flush_batch()

        except Exception as e:
            logger.error(f"Stream consumer error: {e}")
            raise
