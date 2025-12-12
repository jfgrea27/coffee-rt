"""V1 order handler - Direct PostgreSQL writes."""

from psycopg import AsyncConnection

from cafe_order_api.db import insert_order
from cafe_order_api.domain import CoffeeOrderRequest, CoffeeOrderResponse
from cafe_order_api.metrics import ORDER_VALUE_TOTAL, ORDERS_CREATED_TOTAL


async def create_order(db: AsyncConnection, order: CoffeeOrderRequest) -> CoffeeOrderResponse:
    """Create a new coffee order via direct PostgreSQL write."""
    order_id = await insert_order(
        db=db,
        drink=order.drink,
        store=order.store,
        price=order.price,
        timestamp=order.timestamp,
    )

    # Record business metrics
    ORDERS_CREATED_TOTAL.labels(drink=order.drink, store=order.store, version="v1").inc()
    ORDER_VALUE_TOTAL.labels(store=order.store).inc(float(order.price))

    return CoffeeOrderResponse(
        id=order_id,
        drink=order.drink,
        store=order.store,
        price=order.price,
        timestamp=order.timestamp,
    )
