"""Tests for v2 order handler - Redis Streams."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shared import Drink, Store

from cafe_order_api.domain import CoffeeOrderRequest
from cafe_order_api.handlers.orders.v2 import STREAM_NAME, create_order


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection."""
    mock = AsyncMock()
    mock.xadd = AsyncMock(return_value=b"1234567890-0")
    return mock


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
async def test_create_order_returns_accepted_status(mock_redis, sample_order):
    """Test that create_order returns accepted status."""
    result = await create_order(redis=mock_redis, order=sample_order)

    assert result["status"] == "accepted"
    assert result["version"] == "v2"
    assert result["stream"] == STREAM_NAME


@pytest.mark.asyncio
async def test_create_order_returns_message_id(mock_redis, sample_order):
    """Test that create_order returns a message ID."""
    result = await create_order(redis=mock_redis, order=sample_order)

    assert "message_id" in result
    assert len(result["message_id"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_create_order_calls_xadd_with_correct_stream(mock_redis, sample_order):
    """Test that create_order adds to the correct Redis stream."""
    await create_order(redis=mock_redis, order=sample_order)

    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == STREAM_NAME


@pytest.mark.asyncio
async def test_create_order_sends_correct_data_to_stream(mock_redis, sample_order):
    """Test that create_order sends correct order data to stream."""
    await create_order(redis=mock_redis, order=sample_order)

    call_args = mock_redis.xadd.call_args
    stream_data = call_args[0][1]

    assert stream_data["drink"] == "cappuccino"
    assert stream_data["store"] == "downtown"
    assert stream_data["price"] == "5.5"
    assert stream_data["version"] == "v2"
    assert "message_id" in stream_data
    assert "timestamp" in stream_data


@pytest.mark.asyncio
async def test_create_order_increments_metrics(mock_redis, sample_order):
    """Test that create_order increments Prometheus metrics."""
    with patch("cafe_order_api.handlers.orders.v2.ORDERS_CREATED_TOTAL") as mock_counter:
        with patch("cafe_order_api.handlers.orders.v2.ORDER_VALUE_TOTAL") as mock_value:
            mock_labels = MagicMock()
            mock_counter.labels.return_value = mock_labels
            mock_value.labels.return_value = mock_labels

            await create_order(redis=mock_redis, order=sample_order)

            mock_counter.labels.assert_called_once_with(
                drink="cappuccino", store="downtown", version="v2"
            )
            mock_labels.inc.assert_called()
            mock_value.labels.assert_called_once_with(store="downtown")


@pytest.mark.asyncio
async def test_create_order_generates_unique_message_ids(mock_redis, sample_order):
    """Test that create_order generates unique message IDs."""
    results = []
    for _ in range(5):
        result = await create_order(redis=mock_redis, order=sample_order)
        results.append(result["message_id"])

    # All message IDs should be unique
    assert len(set(results)) == 5


@pytest.mark.asyncio
async def test_create_order_handles_different_drinks(mock_redis):
    """Test create_order works with different drink types."""
    for drink in [Drink.CAPPUCCINO, Drink.AMERICANO, Drink.LATTE]:
        order = CoffeeOrderRequest(
            drink=drink,
            store=Store.CENTRAL,
            price=5.00,
            timestamp=datetime.now(timezone.utc),
        )

        result = await create_order(redis=mock_redis, order=order)

        assert result["status"] == "accepted"


@pytest.mark.asyncio
async def test_create_order_includes_timestamp_in_stream(mock_redis, sample_order):
    """Test that create_order includes ISO timestamp in stream data."""
    await create_order(redis=mock_redis, order=sample_order)

    call_args = mock_redis.xadd.call_args
    stream_data = call_args[0][1]

    assert stream_data["timestamp"] == "2025-12-09T10:30:00+00:00"
    assert stream_data["timestamp"] == "2025-12-09T10:30:00+00:00"
