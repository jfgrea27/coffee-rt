import os

# App version
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_TITLE = os.getenv("APP_TITLE", "cafe_order_api")

APP_PORT = os.getenv("APP_PORT", "8005")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")

LOG_FILE = os.getenv("LOG_FILE", "logs/cafe_order_api.log")


# Database configuration
POSTGRES_USER = os.getenv("POSTGRES_USER", "coffee-rt")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "coffee-rt_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "coffee-rt")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "coffee_rt")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
DATABASE_URL_SANITIZED = (
    f"postgresql://********:********@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"
REDIS_URL_SANITIZED = f"redis://********:********@{REDIS_HOST}:{REDIS_PORT}"
