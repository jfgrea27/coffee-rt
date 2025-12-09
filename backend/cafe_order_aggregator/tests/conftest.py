"""Test fixtures for cafe order aggregator."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from shared import CoffeeOrder, Drink, Store


@pytest.fixture
def sample_timestamp():
    """Sample timestamp for testing."""
    return datetime(2025, 12, 9, 10, 30, 0)


@pytest.fixture
def sample_orders(sample_timestamp):
    """Create sample orders for testing."""
    return [
        CoffeeOrder(
            id=1,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=sample_timestamp,
        ),
        CoffeeOrder(
            id=2,
            drink=Drink.LATTE,
            store=Store.UPTOWN,
            price=4.75,
            timestamp=sample_timestamp,
        ),
        CoffeeOrder(
            id=3,
            drink=Drink.CAPPUCCINO,
            store=Store.CENTRAL,
            price=5.50,
            timestamp=sample_timestamp,
        ),
        CoffeeOrder(
            id=4,
            drink=Drink.AMERICANO,
            store=Store.SOUTHEND,
            price=3.50,
            timestamp=sample_timestamp,
        ),
        CoffeeOrder(
            id=5,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=sample_timestamp,
        ),
    ]


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection."""
    mock = AsyncMock()
    mock.set = AsyncMock()
    mock.expire = AsyncMock()
    return mock


@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[])
    mock_cursor.execute = AsyncMock()

    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_cm.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor = MagicMock(return_value=mock_cursor_cm)

    return mock_conn, mock_cursor
