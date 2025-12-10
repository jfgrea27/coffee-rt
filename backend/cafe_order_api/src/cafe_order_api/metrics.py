"""Prometheus metrics for the Cafe Order API."""

from prometheus_client import Counter, Histogram, Info

# Application info
APP_INFO = Info("cafe_order_api", "Cafe Order API information")

# HTTP request metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Business metrics
ORDERS_CREATED_TOTAL = Counter(
    "orders_created_total",
    "Total number of orders created",
    ["drink", "store"],
)

ORDER_VALUE_TOTAL = Counter(
    "order_value_total",
    "Total value of orders in dollars",
    ["store"],
)

# Connection metrics
DB_CONNECTION_STATUS = Counter(
    "db_connection_status_total",
    "Database connection status changes",
    ["status"],  # success, failure
)

REDIS_CONNECTION_STATUS = Counter(
    "redis_connection_status_total",
    "Redis connection status changes",
    ["status"],  # success, failure
)

# WebSocket metrics
WEBSOCKET_CONNECTIONS = Counter(
    "websocket_connections_total",
    "Total WebSocket connections",
    ["action"],  # connected, disconnected
)
