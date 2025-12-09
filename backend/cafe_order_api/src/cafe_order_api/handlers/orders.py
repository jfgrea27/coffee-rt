"""Order handlers for the cafe order API."""

from psycopg import AsyncConnection

from cafe_order_api.db import insert_order
from cafe_order_api.domain import CoffeeOrderRequest, CoffeeOrderResponse


async def create_order(db: AsyncConnection, order: CoffeeOrderRequest) -> CoffeeOrderResponse:
    """Create a new coffee order."""
    order_id = await insert_order(
        db=db,
        drink=order.drink,
        store=order.store,
        price=order.price,
        timestamp=order.timestamp,
    )
    return CoffeeOrderResponse(
        id=order_id,
        drink=order.drink,
        store=order.store,
        price=order.price,
        timestamp=order.timestamp,
    )
