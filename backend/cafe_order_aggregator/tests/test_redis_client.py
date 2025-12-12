"""Tests for redis_client module."""

import json

import pytest

from cafe_order_aggregator.redis_client import (
    update_hourly_metrics,
    update_recent_orders,
    update_top5_drinks,
)


class TestUpdateHourlyMetrics:
    """Tests for update_hourly_metrics function."""

    @pytest.mark.asyncio
    async def test_sets_correct_key(self, mock_redis):
        """Test that the correct Redis key is used."""
        metrics = {"order_count": 10, "revenue": 50.0, "top_drinks": ["cappuccino"]}

        await update_hourly_metrics(mock_redis, 14, metrics)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "metrics:hourly:14"

    @pytest.mark.asyncio
    async def test_sets_correct_value(self, mock_redis):
        """Test that metrics are JSON serialized correctly."""
        metrics = {"order_count": 10, "revenue": 50.0, "top_drinks": ["cappuccino"]}

        await update_hourly_metrics(mock_redis, 14, metrics)

        call_args = mock_redis.set.call_args
        stored_value = json.loads(call_args[0][1])
        assert stored_value == metrics

    @pytest.mark.asyncio
    async def test_sets_expiration(self, mock_redis):
        """Test that key expiration is set to 25 hours."""
        metrics = {"order_count": 10}

        await update_hourly_metrics(mock_redis, 14, metrics)

        mock_redis.expire.assert_called_once_with("metrics:hourly:14", 25 * 3600)

    @pytest.mark.asyncio
    async def test_handles_hour_0(self, mock_redis):
        """Test that hour 0 is handled correctly."""
        metrics = {"order_count": 5}

        await update_hourly_metrics(mock_redis, 0, metrics)

        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "metrics:hourly:0"

    @pytest.mark.asyncio
    async def test_handles_hour_23(self, mock_redis):
        """Test that hour 23 is handled correctly."""
        metrics = {"order_count": 5}

        await update_hourly_metrics(mock_redis, 23, metrics)

        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "metrics:hourly:23"


class TestUpdateTop5Drinks:
    """Tests for update_top5_drinks function."""

    @pytest.mark.asyncio
    async def test_sets_correct_key(self, mock_redis):
        """Test that the correct Redis key is used."""
        top_drinks = ["cappuccino", "latte", "americano"]

        await update_top5_drinks(mock_redis, top_drinks)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "metrics:top5"

    @pytest.mark.asyncio
    async def test_sets_correct_value(self, mock_redis):
        """Test that top drinks are JSON serialized correctly."""
        top_drinks = ["cappuccino", "latte", "americano"]

        await update_top5_drinks(mock_redis, top_drinks)

        call_args = mock_redis.set.call_args
        stored_value = json.loads(call_args[0][1])
        assert stored_value == top_drinks

    @pytest.mark.asyncio
    async def test_no_expiration_set(self, mock_redis):
        """Test that no expiration is set for top5 drinks."""
        top_drinks = ["cappuccino"]

        await update_top5_drinks(mock_redis, top_drinks)

        mock_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_empty_list(self, mock_redis):
        """Test handling of empty drink list."""
        await update_top5_drinks(mock_redis, [])

        call_args = mock_redis.set.call_args
        stored_value = json.loads(call_args[0][1])
        assert stored_value == []


class TestUpdateRecentOrders:
    """Tests for update_recent_orders function."""

    @pytest.mark.asyncio
    async def test_sets_correct_key(self, mock_redis, sample_orders):
        """Test that the correct Redis key is used."""
        await update_recent_orders(mock_redis, sample_orders)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "orders:recent"

    @pytest.mark.asyncio
    async def test_serializes_orders(self, mock_redis, sample_orders):
        """Test that orders are serialized correctly."""
        await update_recent_orders(mock_redis, sample_orders)

        call_args = mock_redis.set.call_args
        stored_value = json.loads(call_args[0][1])
        assert len(stored_value) == 5
        assert stored_value[0]["drink"] == "cappuccino"
        assert stored_value[0]["store"] == "downtown"
        assert stored_value[0]["price"] == 5.50

    @pytest.mark.asyncio
    async def test_sets_expiration(self, mock_redis, sample_orders):
        """Test that key expiration is set to 2 hours."""
        await update_recent_orders(mock_redis, sample_orders)

        mock_redis.expire.assert_called_once_with("orders:recent", 2 * 3600)

    @pytest.mark.asyncio
    async def test_handles_empty_list(self, mock_redis):
        """Test handling of empty order list."""
        await update_recent_orders(mock_redis, [])

        call_args = mock_redis.set.call_args
        stored_value = json.loads(call_args[0][1])
        assert stored_value == []

    @pytest.mark.asyncio
    async def test_order_contains_id(self, mock_redis, sample_orders):
        """Test that serialized orders contain id."""
        await update_recent_orders(mock_redis, sample_orders)

        call_args = mock_redis.set.call_args
        stored_value = json.loads(call_args[0][1])
        assert "id" in stored_value[0]
        assert stored_value[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_order_contains_timestamp(self, mock_redis, sample_orders):
        """Test that serialized orders contain timestamp."""
        await update_recent_orders(mock_redis, sample_orders)

        call_args = mock_redis.set.call_args
        stored_value = json.loads(call_args[0][1])
        assert "timestamp" in stored_value[0]
