"""Test fixtures for the cafe order API."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from cafe_order_api.app import app
from fastapi.testclient import TestClient
from shared import Drink, Store


@pytest.fixture
def test_client(mock_db_connection):
    """Create a test client for the FastAPI app."""
    # Initialize app state that would normally be set by lifespan
    app.state.db_ready = True
    app.state.db_error = None
    app.state.redis_ready = True
    app.state.redis_error = None
    app.state.db_connection = mock_db_connection
    return TestClient(app)


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection."""
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=(1,))
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_conn


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "drink": Drink.CAPPUCCINO.value,
        "store": Store.DOWNTOWN.value,
        "price": 5.50,
        "timestamp": datetime(2025, 12, 9, 10, 30, 0).isoformat(),
    }


@pytest.fixture
def sample_timestamp():
    """Sample timestamp for testing."""
    return datetime(2025, 12, 9, 10, 30, 0)
