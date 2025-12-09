"""Tests for order handlers."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from cafe_order_api.domain import CoffeeOrderRequest
from cafe_order_api.handlers.orders import create_order
from shared import Drink, Store


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection."""
    return AsyncMock()


@pytest.fixture
def sample_order_request():
    """Create a sample order request."""
    return CoffeeOrderRequest(
        drink=Drink.CAPPUCCINO,
        store=Store.DOWNTOWN,
        price=5.50,
        timestamp=datetime(2025, 12, 9, 10, 30, 0),
    )


@pytest.mark.asyncio
async def test_create_order_returns_response(mock_db_connection, sample_order_request):
    """Test that create_order returns a CoffeeOrderResponse."""
    with patch(
        "cafe_order_api.handlers.orders.insert_order", new_callable=AsyncMock
    ) as mock_insert:
        mock_insert.return_value = 123

        result = await create_order(db=mock_db_connection, order=sample_order_request)

        assert result.id == 123
        assert result.drink == Drink.CAPPUCCINO
        assert result.store == Store.DOWNTOWN
        assert result.price == 5.50
        assert result.timestamp == datetime(2025, 12, 9, 10, 30, 0)


@pytest.mark.asyncio
async def test_create_order_calls_insert_order(mock_db_connection, sample_order_request):
    """Test that create_order calls insert_order with correct parameters."""
    with patch(
        "cafe_order_api.handlers.orders.insert_order", new_callable=AsyncMock
    ) as mock_insert:
        mock_insert.return_value = 1

        await create_order(db=mock_db_connection, order=sample_order_request)

        mock_insert.assert_called_once_with(
            db=mock_db_connection,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=datetime(2025, 12, 9, 10, 30, 0),
        )


@pytest.mark.asyncio
async def test_create_order_with_different_drinks(mock_db_connection):
    """Test create_order with different drink types."""
    with patch(
        "cafe_order_api.handlers.orders.insert_order", new_callable=AsyncMock
    ) as mock_insert:
        mock_insert.return_value = 1

        for drink in Drink:
            order = CoffeeOrderRequest(
                drink=drink,
                store=Store.CENTRAL,
                price=4.00,
                timestamp=datetime(2025, 12, 9, 10, 30, 0),
            )
            result = await create_order(db=mock_db_connection, order=order)
            assert result.drink == drink


@pytest.mark.asyncio
async def test_create_order_with_different_stores(mock_db_connection):
    """Test create_order with different store locations."""
    with patch(
        "cafe_order_api.handlers.orders.insert_order", new_callable=AsyncMock
    ) as mock_insert:
        mock_insert.return_value = 1

        for store in Store:
            order = CoffeeOrderRequest(
                drink=Drink.LATTE,
                store=store,
                price=4.50,
                timestamp=datetime(2025, 12, 9, 10, 30, 0),
            )
            result = await create_order(db=mock_db_connection, order=order)
            assert result.store == store
