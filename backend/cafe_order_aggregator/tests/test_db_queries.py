"""Tests for database queries."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from shared import Drink, Store

from cafe_order_aggregator.db.queries import (
    get_orders_for_hour,
    get_orders_last_30_days,
    get_recent_orders,
)


@pytest.fixture
def mock_db_with_results():
    """Create a mock database that returns sample rows."""

    def create_mock(rows):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=rows)
        mock_cursor.execute = AsyncMock()

        mock_cursor_cm = MagicMock()
        mock_cursor_cm.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_cm.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_cm)

        return mock_conn, mock_cursor

    return create_mock


class TestGetOrdersForHour:
    """Tests for get_orders_for_hour function."""

    @pytest.mark.asyncio
    async def test_get_orders_for_hour_returns_orders(self, mock_db_with_results):
        """Test that orders are returned correctly."""
        timestamp = datetime(2025, 12, 9, 10, 30, 0)
        rows = [
            (1, "cappuccino", "downtown", Decimal("5.50"), timestamp),
            (2, "latte", "uptown", Decimal("4.75"), timestamp),
        ]
        mock_conn, mock_cursor = mock_db_with_results(rows)

        result = await get_orders_for_hour(mock_conn, 10)

        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].drink == Drink.CAPPUCCINO
        assert result[0].store == Store.DOWNTOWN
        assert result[0].price == 5.50
        assert result[1].drink == Drink.LATTE

    @pytest.mark.asyncio
    async def test_get_orders_for_hour_empty(self, mock_db_with_results):
        """Test when no orders exist for the hour."""
        mock_conn, mock_cursor = mock_db_with_results([])

        result = await get_orders_for_hour(mock_conn, 10)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_orders_for_hour_executes_query(self, mock_db_with_results):
        """Test that the correct query is executed."""
        mock_conn, mock_cursor = mock_db_with_results([])

        await get_orders_for_hour(mock_conn, 14)

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        query = call_args[0]
        params = call_args[1]

        assert "SELECT" in query
        assert "FROM coffee_rt.orders" in query
        assert "timestamp >=" in query
        assert "timestamp <" in query
        assert len(params) == 2  # start_time and end_time


class TestGetOrdersLast30Days:
    """Tests for get_orders_last_30_days function."""

    @pytest.mark.asyncio
    async def test_get_orders_last_30_days_returns_orders(self, mock_db_with_results):
        """Test that orders are returned correctly."""
        timestamp = datetime(2025, 12, 9, 10, 30, 0)
        rows = [
            (1, "cappuccino", "downtown", Decimal("5.50"), timestamp),
            (2, "americano", "central", Decimal("3.50"), timestamp),
            (3, "latte", "southend", Decimal("4.75"), timestamp),
        ]
        mock_conn, mock_cursor = mock_db_with_results(rows)

        result = await get_orders_last_30_days(mock_conn)

        assert len(result) == 3
        assert result[0].drink == Drink.CAPPUCCINO
        assert result[1].drink == Drink.AMERICANO
        assert result[2].drink == Drink.LATTE

    @pytest.mark.asyncio
    async def test_get_orders_last_30_days_empty(self, mock_db_with_results):
        """Test when no orders exist in last 30 days."""
        mock_conn, mock_cursor = mock_db_with_results([])

        result = await get_orders_last_30_days(mock_conn)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_orders_last_30_days_query(self, mock_db_with_results):
        """Test that query uses 30 day cutoff."""
        mock_conn, mock_cursor = mock_db_with_results([])

        await get_orders_last_30_days(mock_conn)

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        query = call_args[0]
        params = call_args[1]

        assert "timestamp >=" in query
        assert len(params) == 1

        # Verify cutoff is approximately 30 days ago
        cutoff = params[0]
        expected_cutoff = datetime.now() - timedelta(days=30)
        assert abs((cutoff - expected_cutoff).total_seconds()) < 5


class TestGetRecentOrders:
    """Tests for get_recent_orders function."""

    @pytest.mark.asyncio
    async def test_get_recent_orders_returns_orders(self, mock_db_with_results):
        """Test that recent orders are returned correctly."""
        timestamp = datetime.now() - timedelta(minutes=30)
        rows = [
            (1, "cappuccino", "downtown", Decimal("5.50"), timestamp),
        ]
        mock_conn, mock_cursor = mock_db_with_results(rows)

        result = await get_recent_orders(mock_conn)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].drink == Drink.CAPPUCCINO

    @pytest.mark.asyncio
    async def test_get_recent_orders_empty(self, mock_db_with_results):
        """Test when no recent orders exist."""
        mock_conn, mock_cursor = mock_db_with_results([])

        result = await get_recent_orders(mock_conn)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_recent_orders_query(self, mock_db_with_results):
        """Test that query uses 1 hour cutoff."""
        mock_conn, mock_cursor = mock_db_with_results([])

        await get_recent_orders(mock_conn)

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        params = call_args[1]

        # Verify cutoff is approximately 1 hour ago
        cutoff = params[0]
        expected_cutoff = datetime.now() - timedelta(hours=1)
        assert abs((cutoff - expected_cutoff).total_seconds()) < 5
