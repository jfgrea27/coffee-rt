"""Versioned API routers."""

from cafe_order_api.routers.v1 import router as v1_router
from cafe_order_api.routers.v2 import router as v2_router
from cafe_order_api.routers.v3 import router as v3_router

__all__ = ["v1_router", "v2_router", "v3_router"]
