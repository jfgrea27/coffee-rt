"""Tests for v3 API router - Kafka producer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cafe_order_api.app import app
from cafe_order_api.handlers.orders.v3 import KAFKA_TOPIC


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
def client(mock_kafka_producer):
    """Create a test client with mocked dependencies."""
    mock_db_pool = AsyncMock()
    mock_redis = AsyncMock()
    app.state.db_ready = True
    app.state.db_error = None
    app.state.redis_ready = True
    app.state.redis_error = None
    app.state.db_pool = mock_db_pool
    app.state.redis_connection = mock_redis
    app.state.kafka_producer = mock_kafka_producer
    return TestClient(app)


@pytest.fixture
def client_no_kafka():
    """Create a test client without Kafka producer."""
    mock_db_pool = AsyncMock()
    mock_redis = AsyncMock()
    app.state.db_ready = True
    app.state.db_error = None
    app.state.redis_ready = True
    app.state.redis_error = None
    app.state.db_pool = mock_db_pool
    app.state.redis_connection = mock_redis
    app.state.kafka_producer = None
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


class TestV3OrderEndpoint:
    """Tests for POST /api/v3/order endpoint."""

    def test_create_order_success(self, client, sample_order_data):
        """Test successful order creation via Kafka."""
        mock_response = {
            "status": "accepted",
            "version": "v3",
            "topic": KAFKA_TOPIC,
            "partition": 0,
            "offset": 123,
        }

        with patch(
            "cafe_order_api.routers.v3.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.post("/api/v3/order", json=sample_order_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["version"] == "v3"
            assert data["topic"] == KAFKA_TOPIC

    def test_create_order_returns_partition_and_offset(self, client, sample_order_data):
        """Test that response includes partition and offset."""
        mock_response = {
            "status": "accepted",
            "version": "v3",
            "topic": KAFKA_TOPIC,
            "partition": 2,
            "offset": 456,
        }

        with patch(
            "cafe_order_api.routers.v3.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.post("/api/v3/order", json=sample_order_data)

            assert response.status_code == 200
            data = response.json()
            assert data["partition"] == 2
            assert data["offset"] == 456

    def test_create_order_calls_handler(self, client, sample_order_data):
        """Test that endpoint calls the handler."""
        mock_response = {
            "status": "accepted",
            "version": "v3",
            "topic": KAFKA_TOPIC,
            "partition": 0,
            "offset": 0,
        }

        with patch(
            "cafe_order_api.routers.v3.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            client.post("/api/v3/order", json=sample_order_data)

            mock_handler.assert_called_once()

    def test_create_order_kafka_unavailable(self, client_no_kafka, sample_order_data):
        """Test order creation when Kafka producer is not available."""
        response = client_no_kafka.post("/api/v3/order", json=sample_order_data)

        assert response.status_code == 503
        data = response.json()
        assert "Kafka producer not available" in data["detail"]

    def test_create_order_invalid_drink(self, client):
        """Test order creation with invalid drink type."""
        invalid_data = {
            "drink": "invalid_drink",
            "store": "downtown",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00Z",
        }

        response = client.post("/api/v3/order", json=invalid_data)

        assert response.status_code == 422

    def test_create_order_invalid_store(self, client):
        """Test order creation with invalid store."""
        invalid_data = {
            "drink": "cappuccino",
            "store": "invalid_store",
            "price": 5.50,
            "timestamp": "2025-12-09T10:30:00Z",
        }

        response = client.post("/api/v3/order", json=invalid_data)

        assert response.status_code == 422

    def test_create_order_missing_fields(self, client):
        """Test order creation with missing required fields."""
        incomplete_data = {
            "drink": "cappuccino",
        }

        response = client.post("/api/v3/order", json=incomplete_data)

        assert response.status_code == 422

    def test_create_order_handler_error(self, client, sample_order_data):
        """Test that handler errors are propagated."""
        with patch(
            "cafe_order_api.routers.v3.handle_create_order", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = Exception("Kafka error")

            with pytest.raises(Exception, match="Kafka error"):
                client.post("/api/v3/order", json=sample_order_data)

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
                "version": "v3",
                "topic": KAFKA_TOPIC,
                "partition": 0,
                "offset": 0,
            }

            with patch(
                "cafe_order_api.routers.v3.handle_create_order", new_callable=AsyncMock
            ) as mock_handler:
                mock_handler.return_value = mock_response

                response = client.post("/api/v3/order", json=order_data)

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
                "version": "v3",
                "topic": KAFKA_TOPIC,
                "partition": 0,
                "offset": 0,
            }

            with patch(
                "cafe_order_api.routers.v3.handle_create_order", new_callable=AsyncMock
            ) as mock_handler:
                mock_handler.return_value = mock_response

                response = client.post("/api/v3/order", json=order_data)

                assert response.status_code == 200
