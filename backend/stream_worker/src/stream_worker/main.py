"""Main entry point for the stream worker."""

import asyncio
import logging
import signal

from psycopg import AsyncConnection, OperationalError
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from shared.logger import setup_logging

from stream_worker.consumer import consume_stream, ensure_consumer_group
from stream_worker.env import (
    APP_TITLE,
    BATCH_SIZE,
    BATCH_TIMEOUT_MS,
    CONSUMER_GROUP,
    CONSUMER_NAME,
    DATABASE_URL,
    LOG_FILE,
    REDIS_URL,
    STREAM_NAME,
)

setup_logging(LOG_FILE)

logger = logging.getLogger(APP_TITLE)

# Global flag for graceful shutdown
shutdown_event = asyncio.Event()


async def connect_with_retry(
    connect_fn,
    service_name: str,
    max_retries: int = 5,
    initial_backoff: float = 1.0,
):
    """Connect to a service with exponential backoff retry."""
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
    raise last_exception


def handle_shutdown(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


async def run_worker() -> None:
    """Run the stream worker."""
    logger.info("Starting stream worker")
    logger.info(f"Redis URL: {REDIS_URL}")
    logger.info(f"Stream: {STREAM_NAME}")
    logger.info(f"Consumer Group: {CONSUMER_GROUP}")
    logger.info(f"Consumer Name: {CONSUMER_NAME}")

    # Connect to database
    logger.info("Connecting to database...")
    db = await connect_with_retry(
        lambda: AsyncConnection.connect(DATABASE_URL),
        "database",
    )
    logger.info("Database connection established")

    # Connect to Redis
    logger.info("Connecting to Redis...")

    async def connect_redis():
        client = Redis.from_url(REDIS_URL)
        await client.ping()
        return client

    redis = await connect_with_retry(connect_redis, "Redis")
    logger.info("Redis connection established")

    try:
        # Ensure consumer group exists
        await ensure_consumer_group(redis, STREAM_NAME, CONSUMER_GROUP)

        # Run stream consumer in a task so we can monitor shutdown
        consumer_task = asyncio.create_task(
            consume_stream(
                redis,
                db,
                STREAM_NAME,
                CONSUMER_GROUP,
                CONSUMER_NAME,
                batch_size=BATCH_SIZE,
                batch_timeout_ms=BATCH_TIMEOUT_MS,
            )
        )

        # Wait for either shutdown or consumer error
        done, pending = await asyncio.wait(
            [consumer_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Check if consumer task failed
        for task in done:
            if task != consumer_task:
                continue
            if task.exception():
                raise task.exception()

    finally:
        await redis.close()
        await db.close()
        logger.info("Connections closed")


def main() -> None:
    """CLI entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        raise

    logger.info("Stream worker stopped")


if __name__ == "__main__":
    main()
