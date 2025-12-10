"""Environment configuration for cafe order aggregator."""

import os

# App configuration
APP_TITLE = os.getenv("APP_TITLE", "cafe-order-aggregator")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
# Logging configuration
LOG_FILE = os.getenv("LOG_FILE", "logs/aggregator.log")

# Database configuration
POSTGRES_USER = os.getenv("POSTGRES_USER", "coffee-rt")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "coffee-rt_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "coffee-rt")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "coffee_rt")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"
