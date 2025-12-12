"""Tests for v3 order handler - Kafka producer."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from shared import Drink, Store

from cafe_order_api.domain import CoffeeOrderRequest
from cafe_order_api.handlers.orders.v3 import KAFKA_TOPIC, create_order


@pytest.fixture
def mock_kafka_producer():
    """Create a mock Kafka producer."""
    mock = AsyncMock()
    mock_result = MagicMock()
    mock_result.partition = 0
    mock_result.offset = 123
    mock.send_and_wait = AsyncMock(return_value=mock_result)
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
async def test_create_order_returns_accepted_status(mock_kafka_producer, sample_order):
    """Test that create_order returns accepted status."""
    result = await create_order(producer=mock_kafka_producer, order=sample_order)

    assert result["status"] == "accepted"
    assert result["version"] == "v3"
    assert result["topic"] == KAFKA_TOPIC


@pytest.mark.asyncio
async def test_create_order_returns_partition_and_offset(mock_kafka_producer, sample_order):
    """Test that create_order returns partition and offset."""
    result = await create_order(producer=mock_kafka_producer, order=sample_order)

    assert result["partition"] == 0
    assert result["offset"] == 123


@pytest.mark.asyncio
async def test_create_order_calls_send_and_wait(mock_kafka_producer, sample_order):
    """Test that create_order sends message to Kafka."""
    await create_order(producer=mock_kafka_producer, order=sample_order)

    mock_kafka_producer.send_and_wait.assert_called_once()
    call_args = mock_kafka_producer.send_and_wait.call_args
    assert call_args[0][0] == KAFKA_TOPIC


@pytest.mark.asyncio
async def test_create_order_sends_correct_json_data(mock_kafka_producer, sample_order):
    """Test that create_order sends correct JSON data to Kafka."""
    await create_order(producer=mock_kafka_producer, order=sample_order)

    call_args = mock_kafka_producer.send_and_wait.call_args
    message_bytes = call_args[0][1]
    message_data = json.loads(message_bytes.decode("utf-8"))

    assert message_data["drink"] == "cappuccino"
    assert message_data["store"] == "downtown"
    assert message_data["price"] == 5.50
    assert message_data["version"] == "v3"
    assert "message_id" in message_data
    assert "timestamp" in message_data


@pytest.mark.asyncio
async def test_create_order_increments_metrics(mock_kafka_producer, sample_order):
    """Test that create_order increments Prometheus metrics."""
    with patch("cafe_order_api.handlers.orders.v3.ORDERS_CREATED_TOTAL") as mock_counter:
        with patch("cafe_order_api.handlers.orders.v3.ORDER_VALUE_TOTAL") as mock_value:
            mock_labels = MagicMock()
            mock_counter.labels.return_value = mock_labels
            mock_value.labels.return_value = mock_labels

            await create_order(producer=mock_kafka_producer, order=sample_order)

            mock_counter.labels.assert_called_once_with(
                drink="cappuccino", store="downtown", version="v3"
            )
            mock_labels.inc.assert_called()
            mock_value.labels.assert_called_once_with(store="downtown")


@pytest.mark.asyncio
async def test_create_order_raises_http_exception_on_kafka_error(sample_order):
    """Test that create_order raises HTTPException on Kafka error."""
    mock_producer = AsyncMock()
    mock_producer.send_and_wait = AsyncMock(side_effect=Exception("Kafka connection failed"))

    with pytest.raises(HTTPException) as exc_info:
        await create_order(producer=mock_producer, order=sample_order)

    assert exc_info.value.status_code == 503
    assert "Failed to send to Kafka" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_order_does_not_increment_metrics_on_failure(sample_order):
    """Test that metrics are not incremented when Kafka send fails."""
    mock_producer = AsyncMock()
    mock_producer.send_and_wait = AsyncMock(side_effect=Exception("Kafka error"))

    with patch("cafe_order_api.handlers.orders.v3.ORDERS_CREATED_TOTAL") as mock_counter:
        with pytest.raises(HTTPException):
            await create_order(producer=mock_producer, order=sample_order)

        mock_counter.labels.assert_not_called()


@pytest.mark.asyncio
async def test_create_order_generates_unique_message_ids(mock_kafka_producer, sample_order):
    """Test that create_order generates unique message IDs."""
    message_ids = []
    for _ in range(5):
        await create_order(producer=mock_kafka_producer, order=sample_order)
        call_args = mock_kafka_producer.send_and_wait.call_args
        message_bytes = call_args[0][1]
        message_data = json.loads(message_bytes.decode("utf-8"))
        message_ids.append(message_data["message_id"])

    # All message IDs should be unique
    assert len(set(message_ids)) == 5


@pytest.mark.asyncio
async def test_create_order_handles_different_drinks(mock_kafka_producer):
    """Test create_order works with different drink types."""
    for drink in [Drink.CAPPUCCINO, Drink.AMERICANO, Drink.LATTE]:
        order = CoffeeOrderRequest(
            drink=drink,
            store=Store.CENTRAL,
            price=5.00,
            timestamp=datetime.now(timezone.utc),
        )

        result = await create_order(producer=mock_kafka_producer, order=order)

        assert result["status"] == "accepted"
