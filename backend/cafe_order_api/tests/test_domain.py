"""Tests for API-specific domain models."""

import pytest
from cafe_order_api.domain import CoffeeOrderRequest, CoffeeOrderResponse
from pydantic import ValidationError
from shared import Drink, Store


class TestCoffeeOrderRequest:
    """Tests for CoffeeOrderRequest model."""

    def test_valid_order_request(self, sample_timestamp):
        """Test creating a valid order request."""
        order = CoffeeOrderRequest(
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=sample_timestamp,
        )
        assert order.drink == Drink.CAPPUCCINO
        assert order.store == Store.DOWNTOWN
        assert order.price == 5.50
        assert order.timestamp == sample_timestamp

    def test_order_request_with_string_enum_values(self, sample_timestamp):
        """Test creating order request with string values for enums."""
        order = CoffeeOrderRequest(
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
            CoffeeOrderRequest(
                drink="invalid_drink",
                store=Store.DOWNTOWN,
                price=5.50,
                timestamp=sample_timestamp,
            )

    def test_invalid_store_raises_error(self, sample_timestamp):
        """Test that invalid store raises validation error."""
        with pytest.raises(ValidationError):
            CoffeeOrderRequest(
                drink=Drink.CAPPUCCINO,
                store="invalid_store",
                price=5.50,
                timestamp=sample_timestamp,
            )

    def test_request_has_no_id(self, sample_timestamp):
        """Test that request model has id set to None."""
        order = CoffeeOrderRequest(
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=sample_timestamp,
        )
        assert order.id is None


class TestCoffeeOrderResponse:
    """Tests for CoffeeOrderResponse model."""

    def test_valid_order_response(self, sample_timestamp):
        """Test creating a valid order response."""
        response = CoffeeOrderResponse(
            id=1,
            drink=Drink.LATTE,
            store=Store.CENTRAL,
            price=4.75,
            timestamp=sample_timestamp,
        )
        assert response.id == 1
        assert response.drink == Drink.LATTE
        assert response.store == Store.CENTRAL
        assert response.price == 4.75
        assert response.timestamp == sample_timestamp

    def test_response_requires_id(self, sample_timestamp):
        """Test that response model requires an id."""
        with pytest.raises(ValidationError):
            CoffeeOrderResponse(
                drink=Drink.LATTE,
                store=Store.CENTRAL,
                price=4.75,
                timestamp=sample_timestamp,
            )
