"""Tests for v2 API router - Redis Streams."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from cafe_order_api.app import app
from cafe_order_api.handlers.orders.v2 import STREAM_NAME


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection."""
    return AsyncMock()


@pytest.fixture
def client(mock_redis):
    """Create a test client with mocked dependencies."""
    mock_db_pool = AsyncMock()
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


class TestV2OrderEndpoint:
    """Tests for POST /api/v2/order endpoint."""

    def test_create_order_success(self, client, sample_order_data):
        """Test successful order creation via Redis Streams."""
        mock_response = {
            "status": "accepted",
            "version": "v2",
            "stream": STREAM_NAME,
            "message_id": "test-uuid",
        }

        with patch(
            "cafe_order_api.routers.v2.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.post("/api/v2/order", json=sample_order_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["version"] == "v2"
            assert data["stream"] == STREAM_NAME

    def test_create_order_returns_message_id(self, client, sample_order_data):
        """Test that response includes message_id."""
        mock_response = {
            "status": "accepted",
            "version": "v2",
            "stream": STREAM_NAME,
            "message_id": "abc-123-def-456",
        }

        with patch(
            "cafe_order_api.routers.v2.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.post("/api/v2/order", json=sample_order_data)

            assert response.status_code == 200
            data = response.json()
            assert data["message_id"] == "abc-123-def-456"

    def test_create_order_calls_handler(self, client, sample_order_data):
        """Test that endpoint calls the handler."""
        mock_response = {
            "status": "accepted",
            "version": "v2",
            "stream": STREAM_NAME,
            "message_id": "test-uuid",
        }

        with patch(
            "cafe_order_api.routers.v2.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            client.post("/api/v2/order", json=sample_order_data)

            mock_handler.assert_called_once()

    def test_create_order_invalid_drink(self, client):
        """Test order creation with invalid drink type."""
        invalid_data = {
            "drink": "invalid_drink",
            "store": "downtown",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00Z",
        }

        response = client.post("/api/v2/order", json=invalid_data)

        assert response.status_code == 422

    def test_create_order_invalid_store(self, client):
        """Test order creation with invalid store."""
        invalid_data = {
            "drink": "cappuccino",
            "store": "invalid_store",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00Z",
        }

        response = client.post("/api/v2/order", json=invalid_data)

        assert response.status_code == 422

    def test_create_order_missing_fields(self, client):
        """Test order creation with missing required fields."""
        incomplete_data = {
            "drink": "cappuccino",
        }

        response = client.post("/api/v2/order", json=incomplete_data)

        assert response.status_code == 422

    def test_create_order_handler_error(self, client, sample_order_data):
        """Test that handler errors are propagated."""
        with patch(
            "cafe_order_api.routers.v2.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = Exception("Redis error")

            with pytest.raises(Exception, match="Redis error"):
                client.post("/api/v2/order", json=sample_order_data)

    def test_create_order_all_drink_types(self, client):
        """Test order creation with all drink types."""
        for drink in ["cappuccino", "americano", "latte"]:
            order_data = {
                "drink": drink,
                "store": "downtown",
                "price": 5.00,
                "timestamp": "2025-12-09T10:30:00Z",
            }

            mock_response = {
                "status": "accepted",
                "version": "v2",
                "stream": STREAM_NAME,
                "message_id": "test-uuid",
            }

            with patch(
                "cafe_order_api.routers.v2.handle_create_order", new_callable=AsyncMock
            ) as mock_handler:
                mock_handler.return_value = mock_response

                response = client.post("/api/v2/order", json=order_data)

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

            mock_response = {
                "status": "accepted",
                "version": "v2",
                "stream": STREAM_NAME,
                "message_id": "test-uuid",
            }

            with patch(
                "cafe_order_api.routers.v2.handle_create_order", new_callable=AsyncMock
            ) as mock_handler:
                mock_handler.return_value = mock_response

                response = client.post("/api/v2/order", json=order_data)

                assert response.status_code == 200
