"""Tests for database order operations."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from shared import Drink, Store

from cafe_order_api.db.orders import insert_order


@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=(42,))
    mock_cursor.execute = AsyncMock()

    # Setup context manager
    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_cm.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor = MagicMock(return_value=mock_cursor_cm)
    mock_conn.commit = AsyncMock()

    return mock_conn, mock_cursor


@pytest.mark.asyncio
async def test_insert_order_returns_id(mock_db):
    """Test that insert_order returns the generated ID."""
    mock_conn, mock_cursor = mock_db
    timestamp = datetime(2025, 12, 9, 10, 30, 0)

    result = await insert_order(
        db=mock_conn,
        drink=Drink.CAPPUCCINO,
        store=Store.DOWNTOWN,
        price=5.50,
        timestamp=timestamp,
    )

    assert result == 42


@pytest.mark.asyncio
async def test_insert_order_executes_correct_query(mock_db):
    """Test that insert_order executes the correct SQL query."""
    mock_conn, mock_cursor = mock_db
    timestamp = datetime(2025, 12, 9, 10, 30, 0)

    await insert_order(
        db=mock_conn,
        drink=Drink.LATTE,
        store=Store.UPTOWN,
        price=4.75,
        timestamp=timestamp,
    )

    mock_cursor.execute.assert_called_once()
    call_args = mock_cursor.execute.call_args
    query = call_args[0][0]
    params = call_args[0][1]

    assert "INSERT INTO" in query and ".orders" in query
    assert "drink" in query
    assert "store" in query
    assert "price" in query
    assert "timestamp" in query
    assert "RETURNING id" in query
    assert params == ("latte", "uptown", Decimal("4.75"), timestamp)


@pytest.mark.asyncio
async def test_insert_order_commits_transaction(mock_db):
    """Test that insert_order commits the transaction."""
    mock_conn, mock_cursor = mock_db
    timestamp = datetime(2025, 12, 9, 10, 30, 0)

    await insert_order(
        db=mock_conn,
        drink=Drink.AMERICANO,
        store=Store.CENTRAL,
        price=3.50,
        timestamp=timestamp,
    )

    mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_insert_order_uses_enum_values(mock_db):
    """Test that insert_order uses enum string values."""
    mock_conn, mock_cursor = mock_db
    timestamp = datetime(2025, 12, 9, 10, 30, 0)

    await insert_order(
        db=mock_conn,
        drink=Drink.CAPPUCCINO,
        store=Store.SOUTHEND,
        price=5.00,
        timestamp=timestamp,
    )

    call_args = mock_cursor.execute.call_args
    params = call_args[0][1]

    # Verify enum values are used, not enum objects
    assert params[0] == "cappuccino"
    assert params[1] == "southend"
