"""Tests for v1 order handler - Direct PostgreSQL writes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shared import Drink, Store

from cafe_order_api.domain import CoffeeOrderRequest
from cafe_order_api.handlers.orders.v1 import create_order


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection."""
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=(42,))
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_conn


@pytest.fixture
def sample_order():
    """Create a sample order request."""
    return CoffeeOrderRequest(
        drink=Drink.CAPPUCCINO,
        store=Store.DOWNTOWN,
        price=5.50,
        timestamp=datetime(2025, 12, 9, 10, 30, 0, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_create_order_returns_response_with_id(mock_db_connection, sample_order):
    """Test that create_order returns a response with the order ID."""
    with patch(
        "cafe_order_api.handlers.orders.v1.insert_order", new_callable=AsyncMock
    ) as mock_insert:
        mock_insert.return_value = 42

        result = await create_order(db=mock_db_connection, order=sample_order)

        assert result.id == 42
        assert result.drink == Drink.CAPPUCCINO
        assert result.store == Store.DOWNTOWN
        assert result.price == 5.50


@pytest.mark.asyncio
async def test_create_order_calls_insert_order_with_correct_params(
    mock_db_connection, sample_order
):
    """Test that create_order calls insert_order with correct parameters."""
    with patch(
        "cafe_order_api.handlers.orders.v1.insert_order", new_callable=AsyncMock
    ) as mock_insert:
        mock_insert.return_value = 1

        await create_order(db=mock_db_connection, order=sample_order)

        mock_insert.assert_called_once_with(
            db=mock_db_connection,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=sample_order.timestamp,
        )


@pytest.mark.asyncio
async def test_create_order_increments_metrics(mock_db_connection, sample_order):
    """Test that create_order increments Prometheus metrics."""
    with patch(
        "cafe_order_api.handlers.orders.v1.insert_order", new_callable=AsyncMock
    ) as mock_insert:
        with patch("cafe_order_api.handlers.orders.v1.ORDERS_CREATED_TOTAL") as mock_counter:
            with patch("cafe_order_api.handlers.orders.v1.ORDER_VALUE_TOTAL") as mock_value:
                mock_insert.return_value = 1
                mock_labels = MagicMock()
                mock_counter.labels.return_value = mock_labels
                mock_value.labels.return_value = mock_labels

                await create_order(db=mock_db_connection, order=sample_order)

                mock_counter.labels.assert_called_once_with(
                    drink=Drink.CAPPUCCINO, store=Store.DOWNTOWN, version="v1"
                )
                mock_labels.inc.assert_called()
                mock_value.labels.assert_called_once_with(store=Store.DOWNTOWN)


@pytest.mark.asyncio
async def test_create_order_preserves_timestamp(mock_db_connection):
    """Test that create_order preserves the order timestamp."""
    timestamp = datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
    order = CoffeeOrderRequest(
        drink=Drink.LATTE,
        store=Store.UPTOWN,
        price=4.75,
        timestamp=timestamp,
    )

    with patch(
        "cafe_order_api.handlers.orders.v1.insert_order", new_callable=AsyncMock
    ) as mock_insert:
        mock_insert.return_value = 100

        result = await create_order(db=mock_db_connection, order=order)

        assert result.timestamp == timestamp


@pytest.mark.asyncio
async def test_create_order_handles_different_drinks(mock_db_connection):
    """Test create_order works with different drink types."""
    for drink in [Drink.CAPPUCCINO, Drink.AMERICANO, Drink.LATTE]:
        order = CoffeeOrderRequest(
            drink=drink,
            store=Store.CENTRAL,
            price=5.00,
            timestamp=datetime.now(timezone.utc),
        )

        with patch(
            "cafe_order_api.handlers.orders.v1.insert_order", new_callable=AsyncMock
        ) as mock_insert:
            mock_insert.return_value = 1

            result = await create_order(db=mock_db_connection, order=order)

            assert result.drink == drink


@pytest.mark.asyncio
async def test_create_order_handles_different_stores(mock_db_connection):
    """Test create_order works with different store locations."""
    for store in [Store.DOWNTOWN, Store.UPTOWN, Store.CENTRAL, Store.SOUTHEND]:
        order = CoffeeOrderRequest(
            drink=Drink.CAPPUCCINO,
            store=store,
            price=5.00,
            timestamp=datetime.now(timezone.utc),
        )

        with patch(
            "cafe_order_api.handlers.orders.v1.insert_order", new_callable=AsyncMock
        ) as mock_insert:
            mock_insert.return_value = 1

            result = await create_order(db=mock_db_connection, order=order)

            assert result.store == store
