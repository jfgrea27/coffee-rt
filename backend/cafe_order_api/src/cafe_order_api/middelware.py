"""Middleware for FastAPI services."""

import time
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from cafe_order_api.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Track request duration and count."""
        start_time = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start_time
        endpoint = request.url.path
        method = request.method

        # Record metrics
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

        return response


class ServiceHealthMiddleware(BaseHTTPMiddleware):
    """Middleware to check service availability for protected routes."""

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Check if required services are available before processing request.

        Skips health and root endpoints to allow monitoring even when services are down.
        """
        # Allow health check and root endpoints to pass through
        if request.url.path in [
            "/livez",
            "/readyz",
            "/health",
            "/metrics",
            "/",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]:
            return await call_next(request)

        # For all other routes, check service availability
        if not request.app.state.db_ready:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": f"Database connection not available: {request.app.state.db_error}"
                },
            )

        if not request.app.state.redis_ready:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": f"Redis connection not available: {request.app.state.redis_error}"
                },
            )

        return await call_next(request)
