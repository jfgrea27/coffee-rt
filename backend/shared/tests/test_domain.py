"""Tests for shared domain models."""

import pytest
from pydantic import ValidationError

from shared import CoffeeOrder, Drink, Store


class TestDrinkEnum:
    """Tests for the Drink enum."""

    def test_drink_values(self):
        """Test that all drink values are correct."""
        assert Drink.CAPPUCCINO.value == "cappuccino"
        assert Drink.AMERICANO.value == "americano"
        assert Drink.LATTE.value == "latte"

    def test_drink_count(self):
        """Test that we have exactly 3 drinks."""
        assert len(Drink) == 3


class TestStoreEnum:
    """Tests for the Store enum."""

    def test_store_values(self):
        """Test that all store values are correct."""
        assert Store.UPTOWN.value == "uptown"
        assert Store.DOWNTOWN.value == "downtown"
        assert Store.CENTRAL.value == "central"
        assert Store.SOUTHEND.value == "southend"

    def test_store_count(self):
        """Test that we have exactly 4 stores."""
        assert len(Store) == 4


class TestCoffeeOrder:
    """Tests for CoffeeOrder model."""

    def test_valid_order(self, sample_timestamp):
        """Test creating a valid order."""
        order = CoffeeOrder(
            id=1,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=sample_timestamp,
        )
        assert order.id == 1
        assert order.drink == Drink.CAPPUCCINO
        assert order.store == Store.DOWNTOWN
        assert order.price == 5.50
        assert order.timestamp == sample_timestamp

    def test_order_without_id(self, sample_timestamp):
        """Test creating an order without id (for new orders)."""
        order = CoffeeOrder(
            drink=Drink.LATTE,
            store=Store.CENTRAL,
            price=4.75,
            timestamp=sample_timestamp,
        )
        assert order.id is None
        assert order.drink == Drink.LATTE

    def test_order_with_string_enum_values(self, sample_timestamp):
        """Test creating order with string values for enums."""
        order = CoffeeOrder(
            drink="cappuccino",
            store="downtown",
            price=5.50,
            timestamp=sample_timestamp,
        )
        assert order.drink == Drink.CAPPUCCINO
        assert order.store == Store.DOWNTOWN

    def test_invalid_drink_raises_error(self, sample_timestamp):
        """Test that invalid drink raises validation error."""
        with pytest.raises(ValidationError):
            CoffeeOrder(
                drink="invalid_drink",
                store=Store.DOWNTOWN,
                price=5.50,
                timestamp=sample_timestamp,
            )

    def test_invalid_store_raises_error(self, sample_timestamp):
        """Test that invalid store raises validation error."""
        with pytest.raises(ValidationError):
            CoffeeOrder(
                drink=Drink.CAPPUCCINO,
                store="invalid_store",
                price=5.50,
                timestamp=sample_timestamp,
            )
