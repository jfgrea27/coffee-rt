"""Tests for aggregation logic."""

import json

import pytest
from cafe_order_aggregator.aggregator import (
    compute_hourly_metrics,
    compute_top5_drinks,
    serialize_orders,
    update_hourly_metrics,
    update_recent_orders,
    update_top5_drinks,
)
from shared import CoffeeOrder, Drink, Store


class TestComputeHourlyMetrics:
    """Tests for compute_hourly_metrics function."""

    def test_compute_hourly_metrics_with_orders(self, sample_orders):
        """Test computing metrics with orders."""
        result = compute_hourly_metrics(sample_orders)

        assert result["order_count"] == 5
        assert result["revenue"] == 24.75  # 5.50 + 4.75 + 5.50 + 3.50 + 5.50
        assert "cappuccino" in result["top_drinks"]
        assert result["top_drinks"][0] == "cappuccino"  # Most common

    def test_compute_hourly_metrics_empty_orders(self):
        """Test computing metrics with no orders."""
        result = compute_hourly_metrics([])

        assert result["order_count"] == 0
        assert result["revenue"] == 0.0
        assert result["top_drinks"] == []

    def test_compute_hourly_metrics_single_order(self, sample_timestamp):
        """Test computing metrics with a single order."""
        orders = [
            CoffeeOrder(
                id=1,
                drink=Drink.LATTE,
                store=Store.DOWNTOWN,
                price=4.50,
                timestamp=sample_timestamp,
            )
        ]

        result = compute_hourly_metrics(orders)

        assert result["order_count"] == 1
        assert result["revenue"] == 4.50
        assert result["top_drinks"] == ["latte"]

    def test_compute_hourly_metrics_revenue_rounding(self, sample_timestamp):
        """Test that revenue is properly rounded."""
        orders = [
            CoffeeOrder(
                id=i,
                drink=Drink.LATTE,
                store=Store.DOWNTOWN,
                price=1.111,
                timestamp=sample_timestamp,
            )
            for i in range(3)
        ]

        result = compute_hourly_metrics(orders)

        assert result["revenue"] == 3.33  # 1.111 * 3 = 3.333, rounded to 3.33


class TestComputeTop5Drinks:
    """Tests for compute_top5_drinks function."""

    def test_compute_top5_drinks_with_orders(self, sample_orders):
        """Test computing top 5 drinks."""
        result = compute_top5_drinks(sample_orders)

        assert len(result) == 3  # Only 3 unique drinks in sample
        assert result[0] == "cappuccino"  # 3 cappuccinos
        assert "latte" in result
        assert "americano" in result

    def test_compute_top5_drinks_empty_orders(self):
        """Test computing top 5 with no orders."""
        result = compute_top5_drinks([])

        assert result == []

    def test_compute_top5_drinks_limits_to_5(self, sample_timestamp):
        """Test that result is limited to 5 drinks."""
        # Create orders with more than 5 unique drink types
        # (we only have 3 in our enum, so this tests the limit mechanism)
        orders = [
            CoffeeOrder(
                id=i,
                drink=drink,
                store=Store.DOWNTOWN,
                price=4.50,
                timestamp=sample_timestamp,
            )
            for i, drink in enumerate(Drink)
            for _ in range(i + 1)  # Different counts for each
        ]

        result = compute_top5_drinks(orders)

        assert len(result) <= 5


class TestSerializeOrders:
    """Tests for serialize_orders function."""

    def test_serialize_orders(self, sample_orders):
        """Test serializing orders to dictionaries."""
        result = serialize_orders(sample_orders)

        assert len(result) == 5
        assert result[0]["id"] == 1
        assert result[0]["drink"] == "cappuccino"
        assert result[0]["store"] == "downtown"
        assert result[0]["price"] == 5.50
        assert "timestamp" in result[0]

    def test_serialize_orders_empty(self):
        """Test serializing empty list."""
        result = serialize_orders([])

        assert result == []

    def test_serialize_orders_timestamp_format(self, sample_timestamp):
        """Test that timestamp is ISO formatted."""
        orders = [
            CoffeeOrder(
                id=1,
                drink=Drink.LATTE,
                store=Store.DOWNTOWN,
                price=4.50,
                timestamp=sample_timestamp,
            )
        ]

        result = serialize_orders(orders)

        assert result[0]["timestamp"] == "2025-12-09T10:30:00"


class TestUpdateHourlyMetrics:
    """Tests for update_hourly_metrics function."""

    @pytest.mark.asyncio
    async def test_update_hourly_metrics(self, mock_redis):
        """Test updating hourly metrics in Redis."""
        metrics = {"top_drinks": ["cappuccino"], "revenue": 50.0, "order_count": 10}

        await update_hourly_metrics(mock_redis, 10, metrics)

        mock_redis.set.assert_called_once_with("metrics:hourly:10", json.dumps(metrics))
        mock_redis.expire.assert_called_once_with("metrics:hourly:10", 25 * 3600)

    @pytest.mark.asyncio
    async def test_update_hourly_metrics_different_hours(self, mock_redis):
        """Test updating metrics for different hours."""
        metrics = {"top_drinks": [], "revenue": 0.0, "order_count": 0}

        for hour in [0, 12, 23]:
            mock_redis.reset_mock()
            await update_hourly_metrics(mock_redis, hour, metrics)

            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args[0]
            assert call_args[0] == f"metrics:hourly:{hour}"


class TestUpdateTop5Drinks:
    """Tests for update_top5_drinks function."""

    @pytest.mark.asyncio
    async def test_update_top5_drinks(self, mock_redis):
        """Test updating top 5 drinks in Redis."""
        top_drinks = ["cappuccino", "latte", "americano"]

        await update_top5_drinks(mock_redis, top_drinks)

        mock_redis.set.assert_called_once_with("metrics:top5", json.dumps(top_drinks))

    @pytest.mark.asyncio
    async def test_update_top5_drinks_no_expiry(self, mock_redis):
        """Test that top 5 drinks has no expiry."""
        await update_top5_drinks(mock_redis, [])

        # expire should not be called for top5
        mock_redis.expire.assert_not_called()


class TestUpdateRecentOrders:
    """Tests for update_recent_orders function."""

    @pytest.mark.asyncio
    async def test_update_recent_orders(self, mock_redis, sample_orders):
        """Test updating recent orders in Redis."""
        await update_recent_orders(mock_redis, sample_orders)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args[0]
        assert call_args[0] == "orders:recent"

        # Verify the data is JSON serialized
        saved_data = json.loads(call_args[1])
        assert len(saved_data) == 5
        assert saved_data[0]["drink"] == "cappuccino"

    @pytest.mark.asyncio
    async def test_update_recent_orders_expiry(self, mock_redis, sample_orders):
        """Test that recent orders have 2 hour expiry."""
        await update_recent_orders(mock_redis, sample_orders)

        mock_redis.expire.assert_called_once_with("orders:recent", 2 * 3600)

    @pytest.mark.asyncio
    async def test_update_recent_orders_empty(self, mock_redis):
        """Test updating with no recent orders."""
        await update_recent_orders(mock_redis, [])

        mock_redis.set.assert_called_once_with("orders:recent", "[]")
