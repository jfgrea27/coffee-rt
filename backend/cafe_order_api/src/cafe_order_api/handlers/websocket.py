"""WebSocket handler for real-time dashboard updates."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from cafe_order_api.env import DASHBOARD_UPDATE_INTERVAL
from cafe_order_api.handlers.dashboard import get_dashboard

logger = logging.getLogger(__name__)


async def dashboard_websocket_handler(websocket: WebSocket, redis: Redis):
    """Handle WebSocket connections for dashboard updates.

    Sends dashboard data every 30 seconds to connected clients.

    Args:
        websocket: The WebSocket connection
        redis: Redis connection for fetching dashboard data
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            # Fetch and send dashboard data
            logger.info("Fetching dashboard data")
            dashboard_data = await get_dashboard(redis)
            logger.info("Sending dashboard data")
            await websocket.send_json(dashboard_data.model_dump())

            # Wait for next update interval
            await asyncio.sleep(DASHBOARD_UPDATE_INTERVAL)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        raise
