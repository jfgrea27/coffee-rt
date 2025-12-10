"""Utility functions for cafe order API."""

import asyncio
import logging

from psycopg import OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)


async def connect_with_retry(
    connect_fn,
    service_name: str,
    max_retries: int = 3,
    initial_backoff: float = 1.0,
):
    """Connect to a service with exponential backoff retry.

    Args:
        connect_fn: Async function that returns a connection
        service_name: Name of the service for logging
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds

    Returns:
        Connection object or tuple (None, exception) if all retries failed

    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await connect_fn()
        except (OperationalError, RedisConnectionError, OSError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                backoff = initial_backoff * (2**attempt)
                logger.warning(
                    f"Failed to connect to {service_name} "
                    f"(attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {backoff}s..."
                )
                await asyncio.sleep(backoff)
            else:
                logger.error(
                    f"Failed to connect to {service_name} after {max_retries} attempts: {e}"
                )
    return None, last_exception
