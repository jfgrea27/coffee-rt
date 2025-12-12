"""Environment configuration for the stream worker."""

import os
import uuid

APP_TITLE = "stream-worker"

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Database configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "coffee-rt")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "coffee-rt_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "coffee-rt")
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "coffee_rt")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

# Redis Streams configuration
STREAM_NAME = os.getenv("STREAM_NAME", "orders:stream")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "order-workers")
CONSUMER_NAME = os.getenv("CONSUMER_NAME", f"worker-{uuid.uuid4().hex[:8]}")

# Batch configuration
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
BATCH_TIMEOUT_MS = int(os.getenv("BATCH_TIMEOUT_MS", "2000"))

# Logging
LOG_FILE = os.getenv("LOG_FILE", "")
