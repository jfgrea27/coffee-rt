"""Tests for WebSocket handler."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from cafe_order_api.handlers.websocket import dashboard_websocket_handler


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection."""
    return AsyncMock()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_websocket_handler_accepts_connection(mock_websocket, mock_redis):
    """Test that WebSocket handler accepts the connection."""
    mock_redis.get = AsyncMock(return_value=None)

    # Run handler but stop after first iteration
    with patch("cafe_order_api.handlers.websocket.asyncio.sleep", side_effect=Exception("stop")):
        try:
            await dashboard_websocket_handler(mock_websocket, mock_redis)
        except Exception:
            pass

    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_handler_sends_dashboard_data(mock_websocket, mock_redis):
    """Test that WebSocket handler sends dashboard data."""
    hourly_data = json.dumps(
        {
            "top_drinks": ["cappuccino", "latte"],
            "revenue": 100.0,
            "order_count": 20,
        }
    )
    top5_data = json.dumps(["cappuccino", "latte", "americano"])
    recent_data = json.dumps([])

    mock_redis.get = AsyncMock(side_effect=[hourly_data, top5_data, recent_data])

    # Run handler but stop after first iteration
    with patch("cafe_order_api.handlers.websocket.asyncio.sleep", side_effect=Exception("stop")):
        try:
            await dashboard_websocket_handler(mock_websocket, mock_redis)
        except Exception:
            pass

    mock_websocket.send_json.assert_called_once()
    sent_data = mock_websocket.send_json.call_args[0][0]

    assert sent_data["top5_drinks"] == ["cappuccino", "latte", "americano"]
    assert sent_data["current_hour"]["revenue"] == 100.0
    assert sent_data["recent_orders"] == []


@pytest.mark.asyncio
async def test_websocket_handler_handles_disconnect(mock_websocket, mock_redis):
    """Test that WebSocket handler handles client disconnect gracefully."""
    from fastapi import WebSocketDisconnect

    mock_redis.get = AsyncMock(return_value=None)
    mock_websocket.send_json = AsyncMock(side_effect=WebSocketDisconnect())

    # Should not raise an exception
    await dashboard_websocket_handler(mock_websocket, mock_redis)

    mock_websocket.accept.assert_called_once()
