"""Tests for the /api/order endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from cafe_order_api.app import app
from cafe_order_api.domain import CoffeeOrderResponse
from fastapi.testclient import TestClient
from shared import Drink, Store


@pytest.fixture
def client(mock_db_connection):
    """Create a test client."""
    # Initialize app state that would normally be set by lifespan
    app.state.db_ready = True
    app.state.db_error = None
    app.state.redis_ready = True
    app.state.redis_error = None
    app.state.db_connection = mock_db_connection
    return TestClient(app)


@pytest.fixture
def valid_order_payload():
    """Create a valid order payload."""
    return {
        "drink": "cappuccino",
        "store": "downtown",
        "price": 5.50,
        "timestamp": "2025-12-09T10:30:00",
    }


class TestCreateOrderEndpoint:
    """Tests for POST /api/order endpoint."""

    def test_create_order_success(self, client, valid_order_payload):
        """Test successful order creation."""
        mock_response = CoffeeOrderResponse(
            id=1,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=datetime(2025, 12, 9, 10, 30, 0),
        )

        with patch(
            "cafe_order_api.app.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.post("/api/order", json=valid_order_payload)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["drink"] == "cappuccino"
            assert data["store"] == "downtown"
            assert data["price"] == 5.50

    def test_create_order_invalid_drink(self, client):
        """Test order creation with invalid drink."""
        payload = {
            "drink": "invalid_drink",
            "store": "downtown",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00",
        }

        response = client.post("/api/order", json=payload)

        assert response.status_code == 422  # Validation error

    def test_create_order_invalid_store(self, client):
        """Test order creation with invalid store."""
        payload = {
            "drink": "cappuccino",
            "store": "invalid_store",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00",
        }

        response = client.post("/api/order", json=payload)

        assert response.status_code == 422  # Validation error

    def test_create_order_missing_drink(self, client):
        """Test order creation with missing drink field."""
        payload = {
            "store": "downtown",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00",
        }

        response = client.post("/api/order", json=payload)

        assert response.status_code == 422

    def test_create_order_missing_store(self, client):
        """Test order creation with missing store field."""
        payload = {
            "drink": "cappuccino",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00",
        }

        response = client.post("/api/order", json=payload)

        assert response.status_code == 422

    def test_create_order_missing_price(self, client):
        """Test order creation with missing price field."""
        payload = {
            "drink": "cappuccino",
            "store": "downtown",
            "timestamp": "2025-12-09T10:30:00",
        }

        response = client.post("/api/order", json=payload)

        assert response.status_code == 422

    def test_create_order_missing_timestamp(self, client):
        """Test order creation with missing timestamp field."""
        payload = {
            "drink": "cappuccino",
            "store": "downtown",
            "price": 5.50,
        }

        response = client.post("/api/order", json=payload)

        assert response.status_code == 422

    def test_create_order_all_drink_types(self, client):
        """Test order creation with all valid drink types."""
        for drink in Drink:
            mock_response = CoffeeOrderResponse(
                id=1,
                drink=drink,
                store=Store.DOWNTOWN,
                price=5.50,
                timestamp=datetime(2025, 12, 9, 10, 30, 0),
            )

            with patch(
                "cafe_order_api.app.handle_create_order", new_callable=AsyncMock
            ) as mock_handler:
                mock_handler.return_value = mock_response

                payload = {
                    "drink": drink.value,
                    "store": "downtown",
                    "price": 5.50,
                    "timestamp": "2025-12-09T10:30:00",
                }

                response = client.post("/api/order", json=payload)
                assert response.status_code == 200

    def test_create_order_all_store_types(self, client):
        """Test order creation with all valid store types."""
        for store in Store:
            mock_response = CoffeeOrderResponse(
                id=1,
                drink=Drink.CAPPUCCINO,
                store=store,
                price=5.50,
                timestamp=datetime(2025, 12, 9, 10, 30, 0),
            )

            with patch(
                "cafe_order_api.app.handle_create_order", new_callable=AsyncMock
            ) as mock_handler:
                mock_handler.return_value = mock_response

                payload = {
                    "drink": "cappuccino",
                    "store": store.value,
                    "price": 5.50,
                    "timestamp": "2025-12-09T10:30:00",
                }

                response = client.post("/api/order", json=payload)
                assert response.status_code == 200

    def test_create_order_invalid_timestamp_format(self, client):
        """Test order creation with invalid timestamp format."""
        payload = {
            "drink": "cappuccino",
            "store": "downtown",
            "price": 5.50,
            "timestamp": "not-a-timestamp",
        }

        response = client.post("/api/order", json=payload)

        assert response.status_code == 422

    def test_create_order_negative_price(self, client):
        """Test order creation with negative price (should still pass validation)."""
        mock_response = CoffeeOrderResponse(
            id=1,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=-5.50,
            timestamp=datetime(2025, 12, 9, 10, 30, 0),
        )

        with patch(
            "cafe_order_api.app.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            payload = {
                "drink": "cappuccino",
                "store": "downtown",
                "price": -5.50,
                "timestamp": "2025-12-09T10:30:00",
            }

            response = client.post("/api/order", json=payload)
            # Note: Pydantic doesn't validate negative prices by default
            assert response.status_code == 200
