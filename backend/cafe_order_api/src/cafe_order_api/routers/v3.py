"""V3 API router - Kafka producer (durable, exactly-once via idempotent writes)."""

import logging

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, Request

from cafe_order_api.domain import CoffeeOrderRequest
from cafe_order_api.env import APP_TITLE
from cafe_order_api.handlers.orders.v3 import create_order as handle_create_order

logger = logging.getLogger(APP_TITLE)

router = APIRouter(tags=["v3"])


async def get_kafka_producer(request: Request) -> AIOKafkaProducer:
    """Get Kafka producer from app state."""
    producer = request.app.state.kafka_producer
    if producer is None:
        raise HTTPException(status_code=503, detail="Kafka producer not available")
    return producer


@router.post("/order")
async def create_order(
    order: CoffeeOrderRequest, producer: AIOKafkaProducer = Depends(get_kafka_producer)
) -> dict:
    """Create a new coffee order via Kafka."""
    logger.info(f"[v3] Creating order: {order}")
    try:
        res = await handle_create_order(producer=producer, order=order)
        logger.info(f"[v3] Order created: {res}")
        return res
    except Exception as e:
        logger.exception(f"[v3] Failed to create order: {e}")
        raise
