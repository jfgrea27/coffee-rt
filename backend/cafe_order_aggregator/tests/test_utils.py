"""Tests for utils module."""

from shared import CoffeeOrder, Drink, Store

from cafe_order_aggregator.utils import (
    compute_hourly_metrics,
    compute_top5_drinks,
    serialize_orders,
)


class TestComputeHourlyMetrics:
    """Tests for compute_hourly_metrics function."""

    def test_computes_order_count(self, sample_orders):
        """Test that order count is computed correctly."""
        result = compute_hourly_metrics(sample_orders)

        assert result["order_count"] == 5

    def test_computes_revenue(self, sample_orders):
        """Test that revenue is computed correctly."""
        result = compute_hourly_metrics(sample_orders)

        # 5.50 + 4.75 + 5.50 + 3.50 + 5.50 = 24.75
        assert result["revenue"] == 24.75

    def test_computes_top_drinks(self, sample_orders):
        """Test that top drinks are computed correctly."""
        result = compute_hourly_metrics(sample_orders)

        # cappuccino appears 3 times, should be first
        assert result["top_drinks"][0] == "cappuccino"

    def test_handles_empty_orders(self):
        """Test handling of empty order list."""
        result = compute_hourly_metrics([])

        assert result["order_count"] == 0
        assert result["revenue"] == 0.0
        assert result["top_drinks"] == []

    def test_rounds_revenue(self, sample_timestamp):
        """Test that revenue is rounded to 2 decimal places."""
        orders = [
            CoffeeOrder(
                id=1,
                drink=Drink.CAPPUCCINO,
                store=Store.DOWNTOWN,
                price=1.111,
                timestamp=sample_timestamp,
            ),
            CoffeeOrder(
                id=2,
                drink=Drink.LATTE,
                store=Store.UPTOWN,
                price=2.222,
                timestamp=sample_timestamp,
            ),
        ]

        result = compute_hourly_metrics(orders)

        assert result["revenue"] == 3.33

    def test_limits_top_drinks_to_5(self, sample_timestamp):
        """Test that top drinks is limited to 5."""
        orders = []
        drinks = [Drink.CAPPUCCINO, Drink.LATTE, Drink.AMERICANO]
        for i, drink in enumerate(drinks * 3):
            orders.append(
                CoffeeOrder(
                    id=i + 1,
                    drink=drink,
                    store=Store.DOWNTOWN,
                    price=5.0,
                    timestamp=sample_timestamp,
                )
            )

        result = compute_hourly_metrics(orders)

        assert len(result["top_drinks"]) <= 5


class TestComputeTop5Drinks:
    """Tests for compute_top5_drinks function."""

    def test_returns_top_drinks(self, sample_orders):
        """Test that top drinks are returned in order."""
        result = compute_top5_drinks(sample_orders)

        # cappuccino appears 3 times, should be first
        assert result[0] == "cappuccino"

    def test_handles_empty_orders(self):
        """Test handling of empty order list."""
        result = compute_top5_drinks([])

        assert result == []

    def test_limits_to_5_drinks(self, sample_timestamp):
        """Test that result is limited to 5 drinks."""
        orders = []
        drinks = [Drink.CAPPUCCINO, Drink.LATTE, Drink.AMERICANO]
        for i, drink in enumerate(drinks * 3):
            orders.append(
                CoffeeOrder(
                    id=i + 1,
                    drink=drink,
                    store=Store.DOWNTOWN,
                    price=5.0,
                    timestamp=sample_timestamp,
                )
            )

        result = compute_top5_drinks(orders)

        assert len(result) <= 5

    def test_returns_drink_names_as_strings(self, sample_orders):
        """Test that drink names are returned as strings."""
        result = compute_top5_drinks(sample_orders)

        for drink in result:
            assert isinstance(drink, str)

    def test_single_order(self, sample_timestamp):
        """Test with single order."""
        orders = [
            CoffeeOrder(
                id=1,
                drink=Drink.LATTE,
                store=Store.DOWNTOWN,
                price=5.0,
                timestamp=sample_timestamp,
            )
        ]

        result = compute_top5_drinks(orders)

        assert result == ["latte"]


class TestSerializeOrders:
    """Tests for serialize_orders function."""

    def test_serializes_order_id(self, sample_orders):
        """Test that order id is serialized."""
        result = serialize_orders(sample_orders)

        assert result[0]["id"] == 1

    def test_serializes_drink(self, sample_orders):
        """Test that drink is serialized as string value."""
        result = serialize_orders(sample_orders)

        assert result[0]["drink"] == "cappuccino"

    def test_serializes_store(self, sample_orders):
        """Test that store is serialized as string value."""
        result = serialize_orders(sample_orders)

        assert result[0]["store"] == "downtown"

    def test_serializes_price(self, sample_orders):
        """Test that price is serialized."""
        result = serialize_orders(sample_orders)

        assert result[0]["price"] == 5.50

    def test_serializes_timestamp_as_iso(self, sample_orders):
        """Test that timestamp is serialized as ISO format."""
        result = serialize_orders(sample_orders)

        assert result[0]["timestamp"] == "2025-12-09T10:30:00"

    def test_handles_empty_list(self):
        """Test handling of empty order list."""
        result = serialize_orders([])

        assert result == []

    def test_returns_list_of_dicts(self, sample_orders):
        """Test that result is a list of dictionaries."""
        result = serialize_orders(sample_orders)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    def test_preserves_order_count(self, sample_orders):
        """Test that all orders are serialized."""
        result = serialize_orders(sample_orders)

        assert len(result) == len(sample_orders)
