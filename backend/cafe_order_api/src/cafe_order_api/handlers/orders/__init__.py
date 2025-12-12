"""Order handlers for v1, v2, v3 API versions."""

from cafe_order_api.handlers.orders.v1 import create_order as create_order_v1
from cafe_order_api.handlers.orders.v2 import create_order as create_order_v2
from cafe_order_api.handlers.orders.v3 import create_order as create_order_v3

__all__ = ["create_order_v1", "create_order_v2", "create_order_v3"]
