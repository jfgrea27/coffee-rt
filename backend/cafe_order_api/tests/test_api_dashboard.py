"""Tests for the /api/dashboard endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from cafe_order_api.app import app
from cafe_order_api.domain import DashboardResponse, HourlyMetrics, RecentOrder


@pytest.fixture
def client(mock_db_connection):
    """Create a test client."""
    mock_redis = AsyncMock()
    app.state.db_ready = True
    app.state.db_error = None
    app.state.redis_ready = True
    app.state.redis_error = None
    app.state.db_connection = mock_db_connection
    app.state.redis_connection = mock_redis
    return TestClient(app)


class TestDashboardEndpoint:
    """Tests for GET /api/dashboard endpoint."""

    def test_get_dashboard_success(self, client):
        """Test successful dashboard retrieval."""
        mock_response = DashboardResponse(
            current_hour=HourlyMetrics(
                hour=10,
                top_drinks=["cappuccino", "latte"],
                revenue=125.50,
                order_count=25,
            ),
            top5_drinks=["cappuccino", "latte", "americano"],
            recent_orders=[
                RecentOrder(
                    id=1,
                    drink="cappuccino",
                    store="downtown",
                    price=5.50,
                    timestamp="2025-12-09T10:30:00",
                ),
            ],
            server_timestamp=datetime.now(UTC),
        )

        with patch(
            "cafe_order_api.app.handle_get_dashboard", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.get("/api/dashboard")

            assert response.status_code == 200
            data = response.json()
            assert data["current_hour"]["hour"] == 10
            assert data["current_hour"]["top_drinks"] == ["cappuccino", "latte"]
            assert data["current_hour"]["revenue"] == 125.50
            assert data["current_hour"]["order_count"] == 25
            assert data["top5_drinks"] == ["cappuccino", "latte", "americano"]
            assert len(data["recent_orders"]) == 1
            assert data["recent_orders"][0]["drink"] == "cappuccino"

    def test_get_dashboard_empty_metrics(self, client):
        """Test dashboard with no metrics available."""
        mock_response = DashboardResponse(
            current_hour=None,
            top5_drinks=[],
            recent_orders=[],
            server_timestamp=datetime.now(UTC),
        )

        with patch(
            "cafe_order_api.app.handle_get_dashboard", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.get("/api/dashboard")

            assert response.status_code == 200
            data = response.json()
            assert data["current_hour"] is None
            assert data["top5_drinks"] == []
            assert data["recent_orders"] == []

    def test_get_dashboard_partial_metrics(self, client):
        """Test dashboard with only some metrics available."""
        mock_response = DashboardResponse(
            current_hour=None,
            top5_drinks=["cappuccino", "latte"],
            recent_orders=[],
            server_timestamp=datetime.now(UTC),
        )

        with patch(
            "cafe_order_api.app.handle_get_dashboard", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = mock_response

            response = client.get("/api/dashboard")

            assert response.status_code == 200
            data = response.json()
            assert data["current_hour"] is None
            assert data["top5_drinks"] == ["cappuccino", "latte"]
            assert data["recent_orders"] == []
