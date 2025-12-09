"""Shared domain models for Coffee RT services."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Drink(str, Enum):
    """Available drink types."""

    CAPPUCCINO = "cappuccino"
    AMERICANO = "americano"
    LATTE = "latte"


class Store(str, Enum):
    """Available store locations."""

    UPTOWN = "uptown"
    DOWNTOWN = "downtown"
    CENTRAL = "central"
    SOUTHEND = "southend"


class CoffeeOrder(BaseModel):
    """Coffee order model."""

    id: int | None = None
    drink: Drink
    store: Store
    price: float
    timestamp: datetime
