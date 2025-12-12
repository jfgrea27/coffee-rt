"""V2 API router - Redis Streams (durable async processing)."""

import logging

from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis

from cafe_order_api.domain import CoffeeOrderRequest
from cafe_order_api.env import APP_TITLE
from cafe_order_api.handlers.orders.v2 import create_order as handle_create_order

logger = logging.getLogger(APP_TITLE)

router = APIRouter(tags=["v2"])


async def get_redis_connection(request: Request) -> Redis:
    """Get Redis connection from app state."""
    return request.app.state.redis_connection


@router.post("/order")
async def create_order(
    order: CoffeeOrderRequest, redis: Redis = Depends(get_redis_connection)
) -> dict:
    """Create a new coffee order via Redis Streams."""
    logger.info(f"[v2] Creating order: {order}")
    try:
        res = await handle_create_order(redis=redis, order=order)
        logger.info(f"[v2] Order created: {res}")
        return res
    except Exception as e:
        logger.exception(f"[v2] Failed to create order: {e}")
        raise
