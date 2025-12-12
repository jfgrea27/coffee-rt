"""V2 order handler - Redis Streams (durable async processing)."""

import logging
import uuid

from redis.asyncio import Redis

from cafe_order_api.domain import CoffeeOrderRequest
from cafe_order_api.env import APP_TITLE
from cafe_order_api.metrics import ORDER_VALUE_TOTAL, ORDERS_CREATED_TOTAL

logger = logging.getLogger(APP_TITLE)

STREAM_NAME = "orders:stream"


async def create_order(redis: Redis, order: CoffeeOrderRequest) -> dict:
    """
    Create a new coffee order via Redis Streams.

    This uses Redis Streams for durable message delivery - orders are persisted
    in Redis and will be processed by workers even after restarts.

    Unlike Pub/Sub, messages are NOT lost if no consumer is listening.
    """
    # Generate unique message ID for idempotency
    message_id = str(uuid.uuid4())

    # Add order to Redis Stream (stored as hash fields, not JSON)
    stream_id = await redis.xadd(
        STREAM_NAME,
        {
            "message_id": message_id,
            "drink": order.drink.value,
            "store": order.store.value,
            "price": str(order.price),
            "timestamp": order.timestamp.isoformat(),
            "version": "v2",
        },
    )

    # Record metrics immediately (even though DB write is async)
    ORDERS_CREATED_TOTAL.labels(
        drink=order.drink.value, store=order.store.value, version="v2"
    ).inc()
    ORDER_VALUE_TOTAL.labels(store=order.store.value).inc(float(order.price))

    logger.info(f"[v2] Added order to stream {STREAM_NAME}: {message_id} (stream_id={stream_id})")

    return {
        "status": "accepted",
        "version": "v2",
        "stream": STREAM_NAME,
        "message_id": message_id,
    }
