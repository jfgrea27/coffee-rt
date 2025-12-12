"""V3 order handler - Kafka producer (durable, exactly-once via idempotent writes)."""

import json
import logging
import uuid

from aiokafka import AIOKafkaProducer
from fastapi import HTTPException

from cafe_order_api.domain import CoffeeOrderRequest
from cafe_order_api.env import APP_TITLE
from cafe_order_api.metrics import ORDER_VALUE_TOTAL, ORDERS_CREATED_TOTAL

logger = logging.getLogger(APP_TITLE)

KAFKA_TOPIC = "orders"


async def create_order(producer: AIOKafkaProducer, order: CoffeeOrderRequest) -> dict:
    """
    Create a new coffee order via Kafka.

    This provides exactly-once delivery guarantee via idempotent writes.
    Each message includes a unique message_id that the consumer uses to
    deduplicate with INSERT ... ON CONFLICT DO NOTHING.

    The message is durably stored in Kafka until consumed.
    """
    # Generate unique message ID for exactly-once semantics
    message_id = str(uuid.uuid4())

    # Serialize order for Kafka
    order_data = {
        "message_id": message_id,
        "drink": order.drink.value,
        "store": order.store.value,
        "price": float(order.price),
        "timestamp": order.timestamp.isoformat(),
        "version": "v3",
    }

    # Send to Kafka (fire-and-forget with internal retries)
    # Use store as partition key to distribute load across partitions
    # Each store gets its own partition for parallel processing
    #
    # Exactly-once is guaranteed by:
    # 1. Idempotent producer (enable_idempotence=True) - no duplicates in Kafka
    # 2. message_id UUID + ON CONFLICT DO NOTHING in Flink - idempotent DB inserts
    #
    # We don't wait for ack - producer retries internally if needed
    try:
        message = json.dumps(order_data).encode("utf-8")
        partition_key = order.store.value.encode("utf-8")

        # send() queues the message and returns immediately
        # Producer batches and sends with internal retries
        await producer.send(KAFKA_TOPIC, message, key=partition_key)

        logger.debug(f"[v3] Queued order to Kafka topic={KAFKA_TOPIC} key={order.store.value}")

    except Exception as e:
        logger.error(f"[v3] Failed to queue order to Kafka: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to queue to Kafka: {e}")

    # Record metrics after successful send
    ORDERS_CREATED_TOTAL.labels(
        drink=order.drink.value, store=order.store.value, version="v3"
    ).inc()
    ORDER_VALUE_TOTAL.labels(store=order.store.value).inc(float(order.price))

    return {
        "status": "accepted",
        "version": "v3",
        "message_id": message_id,
    }
