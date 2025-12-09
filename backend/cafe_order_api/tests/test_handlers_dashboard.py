"""Tests for dashboard handler."""

import json
from unittest.mock import AsyncMock

import pytest

from cafe_order_api.handlers.dashboard import get_dashboard


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_dashboard_with_all_data(mock_redis):
    """Test get_dashboard returns all metrics when available."""
    # Setup mock data
    hourly_data = json.dumps(
        {
            "top_drinks": ["cappuccino", "latte"],
            "revenue": 125.50,
            "order_count": 25,
        }
    )
    top5_data = json.dumps(["cappuccino", "latte", "americano", "espresso", "mocha"])
    recent_data = json.dumps(
        [
            {
                "id": 1,
                "drink": "cappuccino",
                "store": "downtown",
                "price": 5.50,
                "timestamp": "2025-12-09T10:30:00",
            },
            {
                "id": 2,
                "drink": "latte",
                "store": "uptown",
                "price": 4.75,
                "timestamp": "2025-12-09T10:25:00",
            },
        ]
    )

    mock_redis.get = AsyncMock(side_effect=[hourly_data, top5_data, recent_data])

    result = await get_dashboard(mock_redis)

    assert result.current_hour is not None
    assert result.current_hour.top_drinks == ["cappuccino", "latte"]
    assert result.current_hour.revenue == 125.50
    assert result.current_hour.order_count == 25
    assert result.top5_drinks == ["cappuccino", "latte", "americano", "espresso", "mocha"]
    assert len(result.recent_orders) == 2
    assert result.recent_orders[0].drink == "cappuccino"
    assert result.recent_orders[1].drink == "latte"


@pytest.mark.asyncio
async def test_get_dashboard_with_no_data(mock_redis):
    """Test get_dashboard returns empty data when Redis has no metrics."""
    mock_redis.get = AsyncMock(return_value=None)

    result = await get_dashboard(mock_redis)

    assert result.current_hour is None
    assert result.top5_drinks == []
    assert result.recent_orders == []


@pytest.mark.asyncio
async def test_get_dashboard_with_partial_data(mock_redis):
    """Test get_dashboard handles partial data gracefully."""
    top5_data = json.dumps(["cappuccino", "latte"])

    # Only top5 data available
    mock_redis.get = AsyncMock(side_effect=[None, top5_data, None])

    result = await get_dashboard(mock_redis)

    assert result.current_hour is None
    assert result.top5_drinks == ["cappuccino", "latte"]
    assert result.recent_orders == []


@pytest.mark.asyncio
async def test_get_dashboard_fetches_correct_keys(mock_redis):
    """Test get_dashboard fetches the correct Redis keys."""
    mock_redis.get = AsyncMock(return_value=None)

    await get_dashboard(mock_redis)

    # Verify all three keys were fetched
    calls = mock_redis.get.call_args_list
    assert len(calls) == 3

    # First call should be for hourly metrics (with current hour)
    assert "metrics:hourly:" in calls[0][0][0]

    # Second call should be for top5
    assert calls[1][0][0] == "metrics:top5"

    # Third call should be for recent orders
    assert calls[2][0][0] == "orders:recent"


@pytest.mark.asyncio
async def test_get_dashboard_hourly_metrics_includes_hour(mock_redis):
    """Test that hourly metrics include the hour number."""
    from datetime import datetime

    hourly_data = json.dumps(
        {
            "top_drinks": ["cappuccino"],
            "revenue": 50.0,
            "order_count": 10,
        }
    )

    mock_redis.get = AsyncMock(side_effect=[hourly_data, None, None])

    result = await get_dashboard(mock_redis)

    assert result.current_hour is not None
    assert result.current_hour.hour == datetime.now().hour
