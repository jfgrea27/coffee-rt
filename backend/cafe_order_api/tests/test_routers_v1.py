"""Tests for v1 API router - Direct PostgreSQL writes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from shared import Drink, Store

from cafe_order_api.app import app
from cafe_order_api.domain import CoffeeOrderResponse


@pytest.fixture
def mock_db_pool():
    """Create a mock database connection pool."""
    mock_pool = MagicMock()
    mock_conn = AsyncMock()

    # Setup context manager for pool.connection()
    mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)

    return mock_pool


@pytest.fixture
def client(mock_db_pool):
    """Create a test client with mocked dependencies."""
    mock_redis = AsyncMock()
    app.state.db_ready = True
    app.state.db_error = None
    app.state.redis_ready = True
    app.state.redis_error = None
    app.state.db_pool = mock_db_pool
    app.state.redis_connection = mock_redis
    return TestClient(app)


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "drink": "cappuccino",
        "store": "downtown",
        "price": 5.50,
        "timestamp": "2025-12-09T10:30:00Z",
    }


class TestV1OrderEndpoint:
    """Tests for POST /api/v1/order endpoint."""

    def test_create_order_success(self, client, sample_order_data):
        """Test successful order creation."""
        mock_response = CoffeeOrderResponse(
            id=42,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=datetime(2025, 12, 9, 10, 30, 0, tzinfo=timezone.utc),
        )

        with patch(
            "cafe_order_api.routers.v1.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.post("/api/v1/order", json=sample_order_data)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 42
            assert data["drink"] == "cappuccino"
            assert data["store"] == "downtown"
            assert data["price"] == 5.50

    def test_create_order_calls_handler(self, client, sample_order_data):
        """Test that endpoint calls the handler."""
        mock_response = CoffeeOrderResponse(
            id=1,
            drink=Drink.CAPPUCCINO,
            store=Store.DOWNTOWN,
            price=5.50,
            timestamp=datetime(2025, 12, 9, 10, 30, 0, tzinfo=timezone.utc),
        )

        with patch(
            "cafe_order_api.routers.v1.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            client.post("/api/v1/order", json=sample_order_data)

            mock_handler.assert_called_once()

    def test_create_order_invalid_drink(self, client):
        """Test order creation with invalid drink type."""
        invalid_data = {
            "drink": "invalid_drink",
            "store": "downtown",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00Z",
        }

        response = client.post("/api/v1/order", json=invalid_data)

        assert response.status_code == 422

    def test_create_order_invalid_store(self, client):
        """Test order creation with invalid store."""
        invalid_data = {
            "drink": "cappuccino",
            "store": "invalid_store",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00Z",
        }

        response = client.post("/api/v1/order", json=invalid_data)

        assert response.status_code == 422

    def test_create_order_missing_fields(self, client):
        """Test order creation with missing required fields."""
        incomplete_data = {
            "drink": "cappuccino",
        }

        response = client.post("/api/v1/order", json=incomplete_data)

        assert response.status_code == 422

    def test_create_order_invalid_price(self, client):
        """Test order creation with invalid price."""
        invalid_data = {
            "drink": "cappuccino",
            "store": "downtown",
            "price": "not_a_number",
            "timestamp": "2025-12-09T10:30:00Z",
        }

        response = client.post("/api/v1/order", json=invalid_data)

        assert response.status_code == 422

    def test_create_order_handler_error(self, client, sample_order_data):
        """Test that handler errors are propagated."""
        with patch(
            "cafe_order_api.routers.v1.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                client.post("/api/v1/order", json=sample_order_data)

    def test_create_order_all_drink_types(self, client):
        """Test order creation with all drink types."""
        for drink in ["cappuccino", "americano", "latte"]:
            order_data = {
                "drink": drink,
                "store": "downtown",
                "price": 5.00,
                "timestamp": "2025-12-09T10:30:00Z",
            }

            mock_response = CoffeeOrderResponse(
                id=1,
                drink=Drink(drink),
                store=Store.DOWNTOWN,
                price=5.00,
                timestamp=datetime(2025, 12, 9, 10, 30, 0, tzinfo=timezone.utc),
            )

            with patch(
                "cafe_order_api.routers.v1.handle_create_order", new_callable=AsyncMock
            ) as mock_handler:
                mock_handler.return_value = mock_response

                response = client.post("/api/v1/order", json=order_data)

                assert response.status_code == 200

    def test_create_order_all_store_types(self, client):
        """Test order creation with all store types."""
        for store in ["downtown", "uptown", "central", "southend"]:
            order_data = {
                "drink": "cappuccino",
                "store": store,
                "price": 5.00,
                "timestamp": "2025-12-09T10:30:00Z",
            }

            mock_response = CoffeeOrderResponse(
                id=1,
                drink=Drink.CAPPUCCINO,
                store=Store(store),
                price=5.00,
                timestamp=datetime(2025, 12, 9, 10, 30, 0, tzinfo=timezone.utc),
            )

            with patch(
                "cafe_order_api.routers.v1.handle_create_order", new_callable=AsyncMock
            ) as mock_handler:
                mock_handler.return_value = mock_response

                response = client.post("/api/v1/order", json=order_data)

                assert response.status_code == 200
