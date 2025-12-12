"""V1 API router - Direct PostgreSQL writes."""

import logging

from fastapi import APIRouter, Depends, Request
from psycopg import AsyncConnection

from cafe_order_api.domain import CoffeeOrderRequest, CoffeeOrderResponse
from cafe_order_api.env import APP_TITLE
from cafe_order_api.handlers.orders.v1 import create_order as handle_create_order

logger = logging.getLogger(APP_TITLE)

router = APIRouter(tags=["v1"])


async def get_db_connection(request: Request):
    """Get database connection from pool."""
    async with request.app.state.db_pool.connection() as conn:
        yield conn


@router.post("/order")
async def create_order(
    order: CoffeeOrderRequest, db: AsyncConnection = Depends(get_db_connection)
) -> CoffeeOrderResponse:
    """Create a new coffee order (direct PostgreSQL write)."""
    logger.info(f"[v1] Creating order: {order}")
    try:
        res = await handle_create_order(db=db, order=order)
        logger.info(f"[v1] Order created: {res}")
        return res
    except Exception as e:
        logger.exception(f"[v1] Failed to create order: {e}")
        raise
