"""Domain models for the cafe order API."""

from datetime import datetime

from pydantic import BaseModel
from shared import CoffeeOrder


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    connections: dict


class CoffeeOrderRequest(CoffeeOrder):
    """Coffee order request model."""

    id: None = None


class CoffeeOrderResponse(CoffeeOrder):
    """Coffee order response model."""

    id: int


class HourlyMetrics(BaseModel):
    """Metrics for a specific hour."""

    hour: int
    top_drinks: list[str]
    revenue: float
    order_count: int


class RecentOrder(BaseModel):
    """Recent order from cache."""

    id: int
    drink: str
    store: str
    price: float
    timestamp: str


class DashboardResponse(BaseModel):
    """Dashboard metrics response."""

    current_hour: HourlyMetrics | None
    top5_drinks: list[str]
    recent_orders: list[RecentOrder]
    server_timestamp: datetime
